# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NextOwnerServiceCharge(models.Model):
    """The recurring configuration: "the owners are charged a monthly
    recurring fee of a specified amount... like a service charge from the
    property manager to the property owner" (team review item #11).
    _cron_generate_bills (daily) turns this into an actual next.owner.bill
    each month, on billing_day - the bill is the thing that's actually
    tracked/paid; this is just the standing instruction to create one."""
    _name = 'next.owner.service.charge'
    _description = 'Owner Service Charge (Recurring)'
    _inherit = ['mail.thread']

    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True,
                                domain=[('is_property_owner', '=', True)])
    property_id = fields.Many2one('next.property', string='Property', required=True, tracking=True,
                                   domain="[('owner_ids', 'in', [owner_id])]")
    amount = fields.Monetary(string='Monthly Amount', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                   default=lambda self: self.env.company.currency_id)
    billing_day = fields.Integer(
        default=1, required=True,
        help='Day of the month a bill is raised (1-28, to stay valid in every month).')
    due_days = fields.Integer(
        string='Due Within (days)', default=14,
        help='A bill raised under this schedule is due this many days after it is issued.')
    active = fields.Boolean(default=True, tracking=True)

    bill_ids = fields.One2many('next.owner.bill', 'service_charge_id', string='Bills Raised')
    bill_count = fields.Integer(compute='_compute_bill_count')

    @api.depends('bill_ids')
    def _compute_bill_count(self):
        for rec in self:
            rec.bill_count = len(rec.bill_ids)

    @api.constrains('billing_day')
    def _check_billing_day(self):
        for rec in self:
            if not 1 <= rec.billing_day <= 28:
                raise ValidationError('Billing Day must be between 1 and 28.')

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills - %s' % self.display_name,
            'res_model': 'next.owner.bill',
            'view_mode': 'list,form',
            'domain': [('service_charge_id', '=', self.id)],
        }

    @api.model
    def _cron_generate_bills(self):
        """Daily: for every active charge whose billing_day has arrived this
        month and that doesn't already have a bill for the current period,
        raise one. Idempotent - safe to run daily without duplicating a
        month's bill (next.owner.bill has a uniqueness constraint on
        service_charge_id/period as a second line of defense)."""
        today = fields.Date.context_today(self)
        period_month, period_year = str(today.month), str(today.year)
        charges = self.search([('active', '=', True), ('billing_day', '<=', today.day)])
        for charge in charges:
            exists = self.env['next.owner.bill'].search([
                ('service_charge_id', '=', charge.id),
                ('period_month', '=', period_month), ('period_year', '=', period_year),
            ], limit=1)
            if exists:
                continue
            due_date = today + relativedelta(days=charge.due_days or 0)
            self.env['next.owner.bill'].create({
                'owner_id': charge.owner_id.id,
                'property_id': charge.property_id.id,
                'service_charge_id': charge.id,
                'period_month': period_month,
                'period_year': period_year,
                'amount': charge.amount,
                'currency_id': charge.currency_id.id,
                'invoice_date': today,
                'due_date': due_date,
            }).action_issue()
