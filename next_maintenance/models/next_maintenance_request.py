# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MaintenanceRequest(models.Model):
    """Extends Odoo's native `maintenance.request` rather than reinventing a
    parallel model, per the "extend native apps wherever functionality
    overlaps" instruction. Adds room/property scoping, a guest/housekeeping/
    front-desk raised_by_type, the specified state machine, and the
    auto-block-room-while-open behaviour."""
    _inherit = 'maintenance.request'

    next_room_id = fields.Many2one('next.room', string='Room')
    next_property_id = fields.Many2one(related='next_room_id.property_id', store=True, string='Property')

    raised_by_type = fields.Selection([
        ('guest', 'Guest (Portal)'),
        ('housekeeping', 'Housekeeping'),
        ('front_desk', 'Front Desk'),
        ('staff', 'Other Staff'),
    ], default='staff', required=True)

    assigned_officer_id = fields.Many2one(
        'res.users', string='Maintenance Officer',
        domain=lambda self: [('group_ids', 'in', self.env.ref('next_base.group_next_maintenance_officer').id)])

    next_state = fields.Selection([
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('verified', 'Verified'),
    ], default='new', required=True, tracking=True)

    auto_block_room = fields.Boolean(
        default=True, help='While this request is open, automatically set the room to '
                            'grey_blocked, excluding it from booking availability.')

    service_request_id = fields.Many2one('next.service.request', string='Originating Guest Request',
                                          help='Set when this ticket was escalated from a guest '
                                               'service request raised through the portal.')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.auto_block_room and rec.next_room_id:
                rec.next_room_id.action_set_blocked(reason='Maintenance: %s' % rec.name)
            # next_sms: 'New ticket logged' trigger fires to assigned_officer_id here.
        return records

    def write(self, vals):
        # Two independent controls can close a ticket: our own next_state
        # statusbar (via action_verify, below), or native Maintenance's own
        # Kanban - dragging a card to a stage with stage_id.done=True, which
        # officers use day-to-day and which never touches next_state at all.
        # The room must auto-release back to available whichever one closes
        # the ticket - not just when action_verify() happens to be called -
        # otherwise staff fall back to fixing the room status by hand, which
        # is exactly the gap this override closes.
        closing_stage_now = False
        if vals.get('stage_id'):
            closing_stage_now = bool(self.env['maintenance.stage'].browse(vals['stage_id']).done)
        becoming_verified = vals.get('next_state') == 'verified' or closing_stage_now
        newly_closed = self.filtered(lambda r: r.next_state != 'verified') if becoming_verified else self.browse()

        if newly_closed and 'next_state' not in vals:
            # Fold the next_state sync into this same write (one DB write,
            # no re-entering write() recursively) - harmless no-op for any
            # record in self that doesn't belong to newly_closed, since it
            # would already be 'verified'... but to avoid touching those
            # records' next_state unnecessarily, only merge this in when the
            # whole recordset is becoming verified together.
            if newly_closed == self:
                vals = dict(vals, next_state='verified')

        res = super().write(vals)

        for rec in newly_closed:
            if rec.next_state != 'verified':
                rec.next_state = 'verified'  # mixed recordset fallback: see above
            if rec.auto_block_room and rec.next_room_id and rec.next_room_id.status == 'grey_blocked':
                rec.next_room_id.action_clear_block()
            if rec.service_request_id:
                rec.service_request_id.action_resolve()
        return res

    def action_assign(self, officer=None):
        self.write({'next_state': 'assigned', 'assigned_officer_id': officer.id if officer else self.assigned_officer_id.id})

    def action_start_progress(self):
        self.write({'next_state': 'in_progress'})
        # next_sms: status-update trigger to guest (if guest-reported) + room owner.

    def action_resolve(self):
        self.write({'next_state': 'resolved', 'stage_id': self._get_stage_id('Repaired')})
        # next_sms: status-update trigger to guest (if guest-reported) + room owner.

    def action_verify(self):
        # All the actual work (room release, linked service-request resolve,
        # next_state sync with stage_id) lives in write() above so it applies
        # no matter which control closed the ticket.
        self.write({'next_state': 'verified'})

    def _get_stage_id(self, name):
        stage = self.env['maintenance.stage'].search([('name', '=', name)], limit=1)
        return stage.id if stage else False
