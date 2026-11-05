# -*- coding: utf-8 -*-
import calendar
from datetime import timedelta

from odoo import fields, models


class NextOccupancyReportWizard(models.TransientModel):
    """Team review item #10: "Occupancy rate per property is also critical...
    you need to work out something on this so we can get it per period
    monthly or weekly or year."

    Resolves the chosen period into a concrete date range and reuses
    next.bi.reservation.report.get_kpis() (next_bi_report.py) - which
    already computes occupancy_rate, ADR and RevPAR for a property/date
    range - per property in scope, rather than inventing a second
    occupancy calculation."""
    _name = 'next.occupancy.report.wizard'
    _description = 'Occupancy Rate Report Wizard'

    property_ids = fields.Many2many('next.property', string='Properties',
                                     help='Leave empty to include every property.')
    period_type = fields.Selection([
        ('week', 'Week'), ('month', 'Month'), ('year', 'Year'),
    ], default='month', required=True)
    anchor_date = fields.Date(default=fields.Date.context_today, required=True,
                               help='Any date inside the week/month/year to report on.')
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

    def action_compute(self):
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        properties = self.property_ids or self.env['next.property'].search([])
        Report = self.env['next.bi.reservation.report']
        rows = []
        for prop in properties:
            kpis = Report.get_kpis(
                property_id=prop.id, date_from=fields.Date.to_string(date_from),
                date_to=fields.Date.to_string(date_to))
            rows.append((prop, kpis))
        rows.sort(key=lambda r: r[1]['occupancy_rate'], reverse=True)

        currency_symbol = self.env.company.currency_id.symbol or ''
        row_html = ''.join('''<tr>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;">%s</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%.2f%%</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
            <td style="padding:6px;border-bottom:1px solid #E5E7EB;text-align:right;">%s%.2f</td>
        </tr>''' % (prop.name, kpis['occupancy_rate'], currency_symbol, kpis['adr'],
                    currency_symbol, kpis['revpar'], currency_symbol, kpis['gross_revenue'])
            for prop, kpis in rows)
        self.result_html = '''<div>
            <p><strong>%s</strong> to <strong>%s</strong></p>
            <table style="width:100%%;border-collapse:collapse;font-size:13px;">
                <thead><tr style="background:#F9FAFB;text-align:left;">
                    <th style="padding:6px;">Property</th>
                    <th style="padding:6px;text-align:right;">Occupancy Rate</th>
                    <th style="padding:6px;text-align:right;">ADR</th>
                    <th style="padding:6px;text-align:right;">RevPAR</th>
                    <th style="padding:6px;text-align:right;">Gross Revenue</th>
                </tr></thead>
                <tbody>%s</tbody>
            </table>
        </div>''' % (date_from, date_to, row_html)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'next.occupancy.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
