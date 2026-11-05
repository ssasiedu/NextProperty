# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextProfitabilityReportWizard(models.TransientModel):
    """Team review item #9: "since we capture expense per property and
    room, on the dashboard of the business give a profitability analysis
    of the property drill down to rooms so the business knows which
    property is doing well."

    Reuses next.room.compute_internal_net_income() (next_room_expense.py) -
    already the one place room revenue minus allocated expenses is worked
    out - for every room at every in-scope property for one calendar month,
    rolls it up to a property total, and ranks properties by net income so
    management can see at a glance which property is carrying the business
    and which is lagging, then drill into exactly which room is why."""
    _name = 'next.profitability.report.wizard'
    _description = 'Property Profitability Report Wizard'

    property_ids = fields.Many2many('next.property', string='Properties',
                                     help='Leave empty to include every property.')
    period_month = fields.Selection([(str(i), str(i)) for i in range(1, 13)], required=True,
                                     default=lambda self: str(fields.Date.today().month))
    period_year = fields.Char(required=True, default=lambda self: str(fields.Date.today().year))

    def action_generate_report(self):
        self.ensure_one()
        properties = self.property_ids or self.env['next.property'].search([])
        return self.env.ref('next_owner_portal.action_report_next_profitability').report_action(
            properties, data={'period_month': self.period_month, 'period_year': self.period_year})
