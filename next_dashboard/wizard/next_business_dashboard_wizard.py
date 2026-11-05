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
    maintenance.equipment._get_director_report_data() for the maintenance
    backlog, next.owner.bill for billing/defaulters, next.housekeeping.task
    for the housekeeping backlog, next.qr.order for F&B self-order revenue.
    This wizard is the rollup, not a second source of truth."""
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

    def _get_date_range(self):
        self.ensure_one()
        anchor = self.anchor_date
        if self.period_type == 'week':
            date_from = anchor - timedelta(days=anchor.weekday())
            date_to = date_from + timedelta(days=6)
        elif self.period_type == 'month':
            last_day = calendar.monthrange(anchor.year, anchor.month)[1]
            date_from = anchor.replace(day=1)
            date_to = anchor.replace(day=last_day)
        else:
            date_from = anchor.replace(month=1, day=1)
            date_to = anchor.replace(month=12, day=31)
        return date_from, date_to

    def _get_business_snapshot(self):
        """The one dict used by both the in-app Html preview (action_compute)
        and the PDF Director's Report template - so the two never drift
        apart from each other."""
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        period_month, period_year = str(self.anchor_date.month), str(self.anchor_date.year)

        # Occupancy / revenue - whole business, across every property.
        kpis = self.env['next.bi.reservation.report'].get_kpis(
            property_id=False, date_from=fields.Date.to_string(date_from),
            date_to=fields.Date.to_string(date_to))

        # Property/room profitability - calendar-month granularity only
        # (next.room.compute_internal_net_income is monthly), so this
        # section always reflects the month the anchor date falls in,
        # regardless of the week/year period chosen above.
        properties = self.env['next.property'].search([])
        profitability = sorted(
            (p._get_profitability_breakdown(period_month, period_year) for p in properties),
            key=lambda b: b['net_income'], reverse=True)

        # Maintenance - always a live snapshot (overdue/due-soon/backlog are
        # states, not period-bound figures).
        maintenance = self.env['maintenance.equipment']._get_director_report_data()

        # Owner billing: collection performance for the selected month, and
        # who is a defaulter right now (a live status, independent of which
        # period is being analysed here).
        Bill = self.env['next.owner.bill']
        period_bills = Bill.search([
            ('period_month', '=', period_month), ('period_year', '=', period_year),
            ('state', '=', 'issued')])
        current_defaulters = Bill.search([('is_defaulter', '=', True)])
        pending_reports = Bill.search([('has_pending_report', '=', True)])

        # Housekeeping - live backlog snapshot.
        Task = self.env['next.housekeeping.task']
        housekeeping = {label: Task.search_count([('state', '=', state)])
                        for state, label in Task._fields['state'].selection}

        # F&B / guest QR self-order revenue for the selected period.
        qr_orders = self.env['next.qr.order'].search([
            ('create_date', '>=', date_from), ('create_date', '<=', date_to)])

        return {
            'date_from': date_from, 'date_to': date_to,
            'period_month': period_month, 'period_year': period_year,
            'kpis': kpis,
            'profitability': profitability,
            'total_net_income': sum(b['net_income'] for b in profitability),
            'maintenance': maintenance,
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
        currency_symbol = self.env.company.currency_id.symbol or ''
        kpis, maint, billing = snap['kpis'], snap['maintenance'], snap['billing']

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

        profit_rows = ''.join('''<tr>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;font-weight:600;color:%s;">%s%.2f</td>
        </tr>''' % (b['property'].name, currency_symbol, b['revenue'],
                    '#027A48' if b['net_income'] >= 0 else '#B42318', currency_symbol, b['net_income'])
            for b in snap['profitability'])

        hk_rows = ''.join('<tr><td style="padding:4px 6px;">%s</td><td style="padding:4px 6px;text-align:right;">%s</td></tr>' % (
            label, count) for label, count in snap['housekeeping'].items())

        self.result_html = '''<div style="font-family:Arial,Helvetica,sans-serif;">
            <p style="color:#6B7280;"><strong>%s</strong> to <strong>%s</strong>
               &#8212; profitability/billing figures are for calendar month %s/%s.</p>
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

            <h4 style="margin-bottom:4px;">Housekeeping Backlog (live)</h4>
            <table style="width:260px;border-collapse:collapse;font-size:13px;">%s</table>
        </div>''' % (
            snap['date_from'], snap['date_to'], snap['period_month'], snap['period_year'],
            tiles_row1, tiles_row2, profit_rows or
            '<tr><td colspan="3" style="padding:6px;color:#6B7280;">No properties.</td></tr>', hk_rows)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'next.business.dashboard.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

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
