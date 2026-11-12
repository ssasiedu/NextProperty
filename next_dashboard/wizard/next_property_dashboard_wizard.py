# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextPropertyDashboardWizard(models.TransientModel):
    """Client follow-up to item #12: "a dashboard for the manager of the
    property at each property level where full details like that of the
    executive director will be presented just that this one will be per
    property."

    Not a second dashboard implementation - every figure, the whole HTML
    layout, and the PDF structure are the exact same ones
    next.business.dashboard.wizard already builds (_compute_business_snapshot
    / _render_snapshot_html), just called with this wizard's property_id
    instead of False. The two dashboards can never drift apart from each
    other because there's only one aggregator and one renderer between them."""
    _name = 'next.property.dashboard.wizard'
    _description = 'Property Manager Dashboard'

    property_id = fields.Many2one('next.property', string='Property', required=True)
    period_type = fields.Selection([
        ('week', 'Week'), ('month', 'Month'), ('year', 'Year'),
    ], default='month', required=True)
    anchor_date = fields.Date(default=fields.Date.context_today, required=True,
                               help='Any date inside the week/month/year to report on. '
                                    'Property/room profitability and owner-billing figures '
                                    'are always for the calendar month this date falls in.')
    result_html = fields.Html(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # A manager who runs exactly one property shouldn't have to pick it
        # every time - next.property.manager_id is the existing "who runs
        # this property" field (next_base/views/next_property_views.xml).
        # Anyone managing more than one (or none) still gets a blank field
        # to choose from, same as a director browsing any property.
        if 'property_id' in fields_list and not res.get('property_id'):
            my_properties = self.env['next.property'].search([('manager_id', '=', self.env.user.id)])
            if len(my_properties) == 1:
                res['property_id'] = my_properties.id
        return res

    def _get_date_range(self):
        self.ensure_one()
        return self.env['next.business.dashboard.wizard']._compute_date_range(self.period_type, self.anchor_date)

    def _get_property_snapshot(self):
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        period_month, period_year = str(self.anchor_date.month), str(self.anchor_date.year)
        return self.env['next.business.dashboard.wizard']._compute_business_snapshot(
            date_from, date_to, period_month, period_year, property_id=self.property_id.id)

    def action_compute(self):
        self.ensure_one()
        snap = self._get_property_snapshot()
        self.result_html = self.env['next.business.dashboard.wizard']._render_snapshot_html(snap)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'next.property.dashboard.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_property_report(self):
        self.ensure_one()
        return self.env.ref('next_dashboard.action_report_next_property_manager').report_action(self)
