# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    """Extends Odoo's native `maintenance.equipment` (not a parallel model,
    same reasoning as next_maintenance_request.py) with NEXT's property/room
    scoping and a preventive-maintenance due-date engine:

    A supervisor records a piece of equipment, sets how often it needs
    servicing (preventive_interval_days) and when it's next due
    (next_maintenance_date). _cron_check_preventive_maintenance (wired in
    data/next_maintenance_cron.xml, runs daily) then:
      - opens a `maintenance.request` (type=preventive) alert_lead_days
        before the due date, assigned to the supervisor - one per due
        cycle, tracked via preventive_request_id so it's never duplicated;
      - if that ticket is still open overdue_grace_days past the due date,
        flags the equipment overdue and posts a one-off overdue_penalty
        cost line - "add the cost if not worked on time";
      - once the ticket is actually verified (next_maintenance_request.py's
        write() override calls action_log_maintenance_done below), rolls
        next_maintenance_date forward by preventive_interval_days, so a
        recurring item re-schedules itself with no further input.

    The three _notify_* hooks default to a chatter message + activity (so
    the due-date engine and cost tracking are fully self-contained even
    without next_sms installed, matching the "extend, don't duplicate"
    build order used throughout this suite); next_sms overrides them to
    also fire SMS/email via its send_trigger() - see
    next_sms/models/trigger_equipment.py.
    """
    _inherit = 'maintenance.equipment'

    next_property_id = fields.Many2one('next.property', string='Property', index=True)
    next_room_id = fields.Many2one(
        'next.room', string='Room',
        domain="[('property_id', '=', next_property_id)]",
        help='Leave empty for property-wide equipment (generator, pool pump, lobby AC...).')

    maintenance_supervisor_id = fields.Many2one(
        'res.users', string='Responsible Supervisor',
        domain=lambda self: [
            ('group_ids', 'in', self.env.ref('next_base.group_next_maintenance_supervisor').id)],
        help="Assigned the preventive ticket the cron opens, and alerted (chatter activity, "
             "plus SMS/email if next_sms is installed) as this equipment's maintenance comes "
             "due and if it goes overdue.")

    preventive_interval_days = fields.Integer(
        string='Preventive Interval (days)', default=0,
        help='How often this equipment needs preventive maintenance, e.g. 90 for quarterly. '
             '0 = one-off / not on a recurring schedule - set Next Due Date by hand each time.')
    next_maintenance_date = fields.Date(
        string='Next Preventive Maintenance Due',
        help='A ticket is opened automatically Alert Lead Time days before this date.')
    alert_lead_days = fields.Integer(
        string='Alert Lead Time (days)', default=7,
        help='Open a ticket and start alerting this many days before the due date.')
    overdue_grace_days = fields.Integer(
        string='Overdue Grace Period (days)', default=3,
        help='Days past the due date before this counts as overdue and the overdue penalty '
             'cost below is posted.')
    overdue_penalty_amount = fields.Float(
        string='Overdue Penalty Cost', default=0.0,
        help="Posted once to this equipment's cost log if preventive maintenance is still open "
             "Overdue Grace Period days after the due date - the cost of letting it slide.")

    preventive_request_id = fields.Many2one(
        'maintenance.request', string='Open Preventive Ticket', copy=False, readonly=True,
        help="This due cycle's cron-opened preventive maintenance ticket, if any - tracked so "
             "the cron never opens a second one for the same due date.")
    preventive_overdue = fields.Boolean(
        string='Overdue', default=False, copy=False, readonly=True)

    cost_line_ids = fields.One2many('next.equipment.cost.line', 'equipment_id', string='Cost Log')
    total_maintenance_cost = fields.Float(
        compute='_compute_total_maintenance_cost', store=True, string='Total Maintenance Cost')

    days_until_due = fields.Integer(
        compute='_compute_days_until_due', string='Days Until Due',
        help='Negative once overdue. Blank when there is no schedule set.')

    @api.depends('cost_line_ids.amount')
    def _compute_total_maintenance_cost(self):
        for eq in self:
            eq.total_maintenance_cost = sum(eq.cost_line_ids.mapped('amount'))

    @api.depends('next_maintenance_date')
    def _compute_days_until_due(self):
        today = fields.Date.context_today(self)
        for eq in self:
            eq.days_until_due = (eq.next_maintenance_date - today).days if eq.next_maintenance_date else False

    # --- Notification hooks: default is chatter + activity only. next_sms
    # (installed after this module) extends these with super() + send_trigger
    # so SMS/email go out too, without this module depending on next_sms. ---
    def _notify_preventive_due_soon(self):
        for eq in self:
            eq.message_post(body='Preventive maintenance due on %s.' % eq.next_maintenance_date)
            if eq.maintenance_supervisor_id:
                eq.activity_schedule(
                    'mail.mail_activity_data_todo',
                    date_deadline=eq.next_maintenance_date,
                    summary='Preventive maintenance due: %s' % eq.name,
                    user_id=eq.maintenance_supervisor_id.id)

    def _notify_preventive_overdue(self):
        for eq in self:
            eq.message_post(body='Preventive maintenance is now OVERDUE (was due %s). '
                                  'Overdue penalty of %.2f logged.' % (
                                      eq.next_maintenance_date, eq.overdue_penalty_amount))

    def _notify_preventive_completed(self, cost):
        for eq in self:
            eq.message_post(body='Preventive maintenance completed (cost: %.2f). Next due: %s.' % (
                cost, eq.next_maintenance_date or 'not scheduled'))

    # --- Core engine: called daily by ir_cron_next_equipment_preventive_check ---
    @api.model
    def _cron_check_preventive_maintenance(self):
        today = fields.Date.context_today(self)
        equipments = self.search([('active', '=', True), ('next_maintenance_date', '!=', False)])
        for eq in equipments:
            due = eq.next_maintenance_date
            lead_start = due - timedelta(days=eq.alert_lead_days or 0)
            grace_end = due + timedelta(days=eq.overdue_grace_days or 0)

            # The open ticket may have been closed/removed by some path that
            # didn't go through action_log_maintenance_done - don't let a
            # stale reference block a fresh cycle from ever opening again.
            if eq.preventive_request_id and (
                    not eq.preventive_request_id.exists() or eq.preventive_request_id.next_state == 'verified'):
                eq.preventive_request_id = False

            if today >= lead_start and not eq.preventive_request_id:
                req = self.env['maintenance.request'].create({
                    'name': 'Preventive maintenance: %s' % eq.name,
                    'equipment_id': eq.id,
                    'next_room_id': eq.next_room_id.id,
                    'maintenance_type': 'preventive',
                    'schedule_date': fields.Datetime.to_string(due),
                    'assigned_officer_id': eq.maintenance_supervisor_id.id,
                    'next_state': 'assigned' if eq.maintenance_supervisor_id else 'new',
                    'auto_block_room': False,
                })
                eq.preventive_request_id = req.id
                eq._notify_preventive_due_soon()

            if today > grace_end and not eq.preventive_overdue and eq.preventive_request_id \
                    and eq.preventive_request_id.next_state != 'verified':
                eq.preventive_overdue = True
                if eq.overdue_penalty_amount:
                    self.env['next.equipment.cost.line'].create({
                        'equipment_id': eq.id,
                        'cost_type': 'overdue_penalty',
                        'amount': eq.overdue_penalty_amount,
                        'description': 'Overdue penalty - preventive maintenance not completed by %s' % grace_end,
                        'maintenance_request_id': eq.preventive_request_id.id,
                    })
                eq._notify_preventive_overdue()

    def action_log_maintenance_done(self, cost=0.0, description=None):
        """Called from next_maintenance_request.py's write() override when a
        preventive ticket against this equipment is verified - logs the
        actual cost (if any), rolls next_maintenance_date forward by
        preventive_interval_days for a recurring item, and clears the
        overdue/open-ticket state so the cron starts a fresh cycle next
        time it's due."""
        for eq in self:
            if cost:
                self.env['next.equipment.cost.line'].create({
                    'equipment_id': eq.id,
                    'cost_type': 'preventive',
                    'amount': cost,
                    'description': description or 'Preventive maintenance completed',
                    'maintenance_request_id': eq.preventive_request_id.id if eq.preventive_request_id else False,
                })
            vals = {'preventive_request_id': False, 'preventive_overdue': False}
            if eq.preventive_interval_days and eq.next_maintenance_date:
                vals['next_maintenance_date'] = eq.next_maintenance_date + timedelta(days=eq.preventive_interval_days)
            eq.write(vals)
            eq._notify_preventive_completed(cost)

    # --- Periodic management report ("the director... periodic report") ---
    @api.model
    def _cron_send_equipment_report(self):
        self._send_equipment_report_to_management()

    def action_send_equipment_report(self):
        """Bound to the Equipment list view's Action menu (see
        next_maintenance_equipment_views.xml) so a supervisor can trigger
        the same report on demand instead of waiting for the monthly cron."""
        self._send_equipment_report_to_management()

    @api.model
    def _send_equipment_report_to_management(self):
        equipments = self.search([('active', '=', True), ('next_property_id', '!=', False)])
        if not equipments:
            return
        managers = self.env['res.users'].search(
            [('group_ids', 'in', self.env.ref('next_base.group_next_manager').id)])
        recipients = managers.mapped('partner_id').filtered('email')
        if not recipients:
            return
        overdue = equipments.filtered('preventive_overdue')
        due_soon = equipments.filtered(
            lambda e: e.next_maintenance_date and e not in overdue
            and e.days_until_due is not False and 0 <= e.days_until_due <= 14)
        total_cost = sum(equipments.mapped('total_maintenance_cost'))
        body_html = self._render_equipment_report_html(equipments, overdue, due_soon, total_cost)
        for partner in recipients:
            self.env['mail.mail'].sudo().create({
                'subject': 'NEXT Property Management - Equipment Maintenance Report',
                'body_html': body_html,
                'email_to': partner.email,
                'auto_delete': False,
            })

    def _render_equipment_report_html(self, equipments, overdue, due_soon, total_cost):
        currency_symbol = self.env.company.currency_id.symbol or ''
        rows = []
        for eq in equipments.sorted(key=lambda e: e.next_maintenance_date or fields.Date.today()):
            status, color = 'OK', '#027A48'
            if eq in overdue:
                status, color = 'OVERDUE', '#B42318'
            elif eq in due_soon:
                status, color = 'DUE SOON', '#B54708'
            rows.append('''<tr>
                <td style="padding:8px;border-bottom:1px solid #E5E7EB;">%s</td>
                <td style="padding:8px;border-bottom:1px solid #E5E7EB;">%s</td>
                <td style="padding:8px;border-bottom:1px solid #E5E7EB;">%s</td>
                <td style="padding:8px;border-bottom:1px solid #E5E7EB;">%s</td>
                <td style="padding:8px;border-bottom:1px solid #E5E7EB;color:%s;font-weight:600;">%s</td>
                <td style="padding:8px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
            </tr>''' % (eq.name, eq.next_property_id.name or '-', eq.next_room_id.name or 'Property-wide',
                        eq.next_maintenance_date or '-', color, status, currency_symbol, eq.total_maintenance_cost))
        return '''<div style="font-family:Arial,Helvetica,sans-serif;color:#1F2937;">
          <h2 style="margin-bottom:4px;">Equipment Maintenance Report</h2>
          <p style="color:#6B7280;margin-top:0;">%s equipment tracked &#8212; %s overdue, %s due within 14 days.
             Total maintenance cost logged: %s%.2f.</p>
          <table style="width:100%%;border-collapse:collapse;font-size:13px;">
            <thead><tr style="background:#F9FAFB;text-align:left;">
              <th style="padding:8px;">Equipment</th><th style="padding:8px;">Property</th>
              <th style="padding:8px;">Room</th><th style="padding:8px;">Next Due</th>
              <th style="padding:8px;">Status</th><th style="padding:8px;text-align:right;">Cost to Date</th>
            </tr></thead>
            <tbody>%s</tbody>
          </table>
        </div>''' % (len(equipments), len(overdue), len(due_soon), currency_symbol, total_cost, ''.join(rows))
