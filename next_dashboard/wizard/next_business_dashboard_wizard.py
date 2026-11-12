# -*- coding: utf-8 -*-
import base64
import calendar
from datetime import timedelta

from odoo import api, fields, models


class NextBusinessDashboardWizard(models.TransientModel):
    """Team review item #12: "There should be an overall dashboard and
    director auto report that gives a 360 view of the entire business."

    Deliberately does not recompute anything that already has a home
    elsewhere in the suite - every figure below is read straight from the
    existing aggregator each module already built for its own slice:
    next.bi.reservation.report.get_kpis() for occupancy/ADR/RevPAR/revenue,
    next.property._get_profitability_breakdown() for property/room P&L,
    maintenance.equipment._get_director_report_data() /
    _get_maintenance_period_snapshot() for the maintenance backlog and
    period activity, next.owner.bill for billing/defaulters,
    next.housekeeping.task for the housekeeping backlog, next.qr.order for
    F&B self-order revenue. This wizard is the rollup, not a second source
    of truth.

    _compute_business_snapshot is a plain @api.model method (not reading
    self's own fields) so next.property.dashboard.wizard - the per-property
    Manager Dashboard - can call straight into it with property_id set,
    without duplicating a single figure's logic."""
    _name = 'next.business.dashboard.wizard'
    _description = 'Executive 360 Dashboard'

    period_type = fields.Selection([
        ('week', 'Week'), ('month', 'Month'), ('year', 'Year'),
    ], default='month', required=True)
    anchor_date = fields.Date(default=fields.Date.context_today, required=True,
                               help='Any date inside the week/month/year to report on. '
                                    'Property/room profitability and owner-billing figures '
                                    'are always for the calendar month this date falls in.')
    result_html = fields.Html(readonly=True)

    def _compute_display_name(self):
        # No 'name' field on this transient wizard, so the breadcrumb/title
        # otherwise falls back to the bare "next.business.dashboard.wizard,2"
        # technical reference - this gives it a readable one instead.
        for rec in self:
            rec.display_name = 'Executive Dashboard - %s %s' % (
                dict(rec._fields['period_type'].selection).get(rec.period_type, ''), rec.anchor_date or '')

    def _get_date_range(self):
        self.ensure_one()
        return self._compute_date_range(self.period_type, self.anchor_date)

    @api.model
    def _compute_date_range(self, period_type, anchor):
        if period_type == 'week':
            date_from = anchor - timedelta(days=anchor.weekday())
            date_to = date_from + timedelta(days=6)
        elif period_type == 'month':
            last_day = calendar.monthrange(anchor.year, anchor.month)[1]
            date_from = anchor.replace(day=1)
            date_to = anchor.replace(day=last_day)
        else:
            date_from = anchor.replace(month=1, day=1)
            date_to = anchor.replace(month=12, day=31)
        return date_from, date_to

    def _get_business_snapshot(self):
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        period_month, period_year = str(self.anchor_date.month), str(self.anchor_date.year)
        return self._compute_business_snapshot(date_from, date_to, period_month, period_year, property_id=False)

    @api.model
    def _compute_business_snapshot(self, date_from, date_to, period_month, period_year, property_id=False):
        """The one dict used by both the in-app Html preview (action_compute)
        and the PDF Director's Report template - so the two never drift
        apart from each other - and, with property_id set, by the
        per-property Manager Dashboard too."""
        # Occupancy / revenue - whole business, or one property when scoped.
        kpis = self.env['next.bi.reservation.report'].get_kpis(
            property_id=property_id or False, date_from=fields.Date.to_string(date_from),
            date_to=fields.Date.to_string(date_to))

        # Property/room profitability - calendar-month granularity only
        # (next.room.compute_internal_net_income is monthly), so this
        # section always reflects the month the anchor date falls in,
        # regardless of the week/year period chosen above.
        properties = self.env['next.property'].browse(property_id) if property_id \
            else self.env['next.property'].search([])
        profitability = sorted(
            (p._get_profitability_breakdown(period_month, period_year) for p in properties),
            key=lambda b: b['net_income'], reverse=True)

        # Maintenance - a live backlog snapshot (overdue/due-soon/open-ticket
        # states aren't period-bound) plus this period's ticket activity and
        # the quantified cost of maintenance not being done.
        Equipment = self.env['maintenance.equipment']
        maintenance = Equipment._get_director_report_data(property_id=property_id)
        maint_period = Equipment._get_maintenance_period_snapshot(date_from, date_to, property_id=property_id)

        # Owner billing: collection performance for the selected month, and
        # who is a defaulter right now (a live status, independent of which
        # period is being analysed here).
        Bill = self.env['next.owner.bill']
        bill_domain = [('period_month', '=', period_month), ('period_year', '=', period_year),
                        ('state', '=', 'issued')]
        defaulter_domain = [('is_defaulter', '=', True)]
        pending_domain = [('has_pending_report', '=', True)]
        if property_id:
            bill_domain.append(('property_id', '=', property_id))
            defaulter_domain.append(('property_id', '=', property_id))
            pending_domain.append(('property_id', '=', property_id))
        period_bills = Bill.search(bill_domain)
        current_defaulters = Bill.search(defaulter_domain)
        pending_reports = Bill.search(pending_domain)

        # Housekeeping - live backlog snapshot.
        Task = self.env['next.housekeeping.task']
        hk_domain = [('property_id', '=', property_id)] if property_id else []
        housekeeping = {label: Task.search_count(hk_domain + [('state', '=', state)])
                        for state, label in Task._fields['state'].selection}

        # F&B / guest QR self-order revenue for the selected period.
        qr_domain = [('create_date', '>=', date_from), ('create_date', '<=', date_to)]
        if property_id:
            qr_domain.append(('room_id.property_id', '=', property_id))
        qr_orders = self.env['next.qr.order'].search(qr_domain)

        return {
            'date_from': date_from, 'date_to': date_to,
            'period_month': period_month, 'period_year': period_year,
            'kpis': kpis,
            'profitability': profitability,
            'total_net_income': sum(b['net_income'] for b in profitability),
            'maintenance': maintenance,
            'maint_period': maint_period,
            'billing': {
                'total_billed': sum(period_bills.mapped('amount')),
                'total_collected': sum(period_bills.mapped('amount_paid')),
                'bill_count': len(period_bills),
                'defaulters': current_defaulters,
                'defaulter_balance': sum(current_defaulters.mapped('balance')),
                'pending_reports': pending_reports,
            },
            'housekeeping': housekeeping,
            'fnb_revenue': sum(qr_orders.mapped('amount_total')),
            'fnb_order_count': len(qr_orders),
        }

    def action_compute(self):
        self.ensure_one()
        snap = self._get_business_snapshot()
        self.result_html = self._render_snapshot_html(snap)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'next.business.dashboard.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _render_snapshot_html(self, snap):
        """Shared by this wizard and next.property.dashboard.wizard - same
        layout, the only difference is what property_id narrowed snap's
        figures down to."""
        currency_symbol = self.env.company.currency_id.symbol or ''
        kpis, maint, maint_period, billing = snap['kpis'], snap['maintenance'], snap['maint_period'], snap['billing']

        def tile(value, label, color='#1F2937'):
            return '''<div style="flex:1;min-width:140px;text-align:center;padding:10px 4px;">
                <div style="font-size:22px;font-weight:700;color:%s;">%s</div>
                <div style="color:#6B7280;font-size:12px;">%s</div>
            </div>''' % (color, value, label)

        tiles_row1 = ''.join([
            tile('%.1f%%' % kpis['occupancy_rate'], 'Occupancy Rate'),
            tile('%s%.2f' % (currency_symbol, kpis['gross_revenue']), 'Gross Revenue'),
            tile('%s%.2f' % (currency_symbol, kpis['adr']), 'ADR'),
            tile('%s%.2f' % (currency_symbol, kpis['revpar']), 'RevPAR'),
            tile('%s%.2f' % (currency_symbol, snap['total_net_income']), 'Net Income (Properties)',
                 '#027A48' if snap['total_net_income'] >= 0 else '#B42318'),
        ])
        tiles_row2 = ''.join([
            tile(len(maint['overdue']), 'Equipment Overdue', '#B42318' if maint['overdue'] else '#027A48'),
            tile(len(maint['open_tickets']), 'Open Maintenance Tickets'),
            tile(len(billing['defaulters']), 'Owner Billing Defaulters',
                 '#B42318' if billing['defaulters'] else '#027A48'),
            tile('%s%.2f' % (currency_symbol, billing['total_collected']), 'Owner Billing Collected (period)'),
            tile('%s%.2f' % (currency_symbol, snap['fnb_revenue']), 'F&B / QR Revenue (period)'),
        ])

        # Maintenance ticket activity for the period, so a director/manager
        # sees the team is actually working - not just today's open count.
        tiles_row3 = ''.join([
            tile(len(maint_period['opened']), 'Tickets Opened (period)'),
            tile(len(maint_period['completed']), 'Tickets Completed (period)', '#027A48'),
            tile(len(maint_period['resolved']), 'Tickets Resolved, Pending Verification'),
            tile(len(maint_period['pending']), 'Tickets Pending (all open)',
                 '#B54708' if maint_period['pending'] else '#027A48'),
            tile('%s%.2f' % (currency_symbol, maint_period['cost_already_incurred']),
                 'Cost of Inaction Incurred (period)', '#B42318' if maint_period['cost_already_incurred'] else '#1F2937'),
        ])

        profit_rows = ''.join('''<tr>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;font-weight:600;color:%s;">%s%.2f</td>
        </tr>''' % (b['property'].name, currency_symbol, b['revenue'],
                    '#027A48' if b['net_income'] >= 0 else '#B42318', currency_symbol, b['net_income'])
            for b in snap['profitability'])

        hk_rows = ''.join('<tr><td style="padding:4px 6px;">%s</td><td style="padding:4px 6px;text-align:right;">%s</td></tr>' % (
            label, count) for label, count in snap['housekeeping'].items())

        upcoming_rows = ''.join('''<tr>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;color:%s;font-weight:600;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
        </tr>''' % (eq.name, eq.next_property_id.name or '-', eq.next_maintenance_date or '-',
                    '#B42318' if eq in maint_period['overdue_equipment'] else '#B54708',
                    'OVERDUE' if eq in maint_period['overdue_equipment'] else 'DUE SOON',
                    currency_symbol, eq.overdue_penalty_amount)
            for eq in maint_period['upcoming_equipment'])

        return '''<div style="font-family:Arial,Helvetica,sans-serif;">
            <p style="color:#6B7280;"><strong>%s</strong> to <strong>%s</strong>
               &#8212; profitability/billing figures are for calendar month %s/%s.</p>
            <div style="display:flex;flex-wrap:wrap;border:1px solid #E5E7EB;border-radius:8px;margin-bottom:8px;">%s</div>
            <div style="display:flex;flex-wrap:wrap;border:1px solid #E5E7EB;border-radius:8px;margin-bottom:8px;">%s</div>
            <div style="display:flex;flex-wrap:wrap;border:1px solid #E5E7EB;border-radius:8px;margin-bottom:16px;">%s</div>

            <h4 style="margin-bottom:4px;">Property Profitability (ranked)</h4>
            <table style="width:100%%;border-collapse:collapse;font-size:13px;margin-bottom:16px;">
                <thead><tr style="background:#F9FAFB;text-align:left;">
                    <th style="padding:6px;">Property</th>
                    <th style="padding:6px;text-align:right;">Revenue</th>
                    <th style="padding:6px;text-align:right;">Net Income</th>
                </tr></thead>
                <tbody>%s</tbody>
            </table>

            <h4 style="margin-bottom:4px;">Upcoming Maintenance (overdue + due within 30 days)</h4>
            <table style="width:100%%;border-collapse:collapse;font-size:13px;margin-bottom:4px;">
                <thead><tr style="background:#F9FAFB;text-align:left;">
                    <th style="padding:6px;">Equipment</th><th style="padding:6px;">Property</th>
                    <th style="padding:6px;">Next Due</th><th style="padding:6px;">Status</th>
                    <th style="padding:6px;text-align:right;">Cost if Not Done</th>
                </tr></thead>
                <tbody>%s</tbody>
            </table>
            <p style="color:#6B7280;font-size:12px;margin-top:0;margin-bottom:16px;">
                "Cost if Not Done" is each item's configured overdue penalty - what gets logged against it
                the moment it passes its grace period unresolved. Total at risk right now:
                <strong style="color:#B42318;">%s%.2f</strong>.
            </p>

            <h4 style="margin-bottom:4px;">Housekeeping Backlog (live)</h4>
            <table style="width:260px;border-collapse:collapse;font-size:13px;">%s</table>
        </div>''' % (
            snap['date_from'], snap['date_to'], snap['period_month'], snap['period_year'],
            tiles_row1, tiles_row2, tiles_row3, profit_rows or
            '<tr><td colspan="3" style="padding:6px;color:#6B7280;">No properties.</td></tr>',
            upcoming_rows or '<tr><td colspan="5" style="padding:6px;color:#6B7280;">Nothing overdue or due soon.</td></tr>',
            currency_symbol, maint_period['cost_at_risk'], hk_rows)

    def action_print_director_report(self):
        self.ensure_one()
        return self.env.ref('next_dashboard.action_report_next_business_director').report_action(self)

    @api.model
    def _cron_generate_monthly_director_report(self):
        """The "director auto report" half of item #12 - runs monthly with
        no one needing to remember to click Print: generates the PDF for
        the month that just ended and emails it to every Manager-group
        user as an attachment."""
        today = fields.Date.context_today(self)
        last_day_prev_month = today.replace(day=1) - timedelta(days=1)
        wizard = self.create({'period_type': 'month', 'anchor_date': last_day_prev_month})

        report = self.env.ref('next_dashboard.action_report_next_business_director')
        pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(report, [wizard.id])
        attachment = self.env['ir.attachment'].create({
            'name': 'Business Director Report - %s.pdf' % last_day_prev_month.strftime('%Y-%m'),
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'next.business.dashboard.wizard',
            'res_id': wizard.id,
        })

        managers = self.env['res.users'].search([
            ('group_ids', 'in', self.env.ref('next_base.group_next_manager').id)])
        for partner in managers.mapped('partner_id'):
            if not partner.email:
                continue
            self.env['mail.mail'].sudo().create({
                'subject': 'Business Director Report - %s' % last_day_prev_month.strftime('%B %Y'),
                'body_html': '<p>Attached: the automated 360 business report for %s.</p>' % (
                    last_day_prev_month.strftime('%B %Y')),
                'email_to': partner.email,
                'attachment_ids': [(6, 0, [attachment.id])],
                'auto_delete': False,
            })
