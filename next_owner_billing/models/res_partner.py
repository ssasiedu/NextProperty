# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    owner_bill_ids = fields.One2many('next.owner.bill', 'owner_id', string='Service Charge Bills')
    owner_billing_balance = fields.Float(
        compute='_compute_owner_billing_balance', string='Service Charge Balance Due',
        help='Total outstanding across every issued service-charge bill, in each bill\'s own '
             'currency added together - this is what the owner dashboard/portal and the billing '
             'director dashboard both show.')
    owner_billing_is_defaulter = fields.Boolean(compute='_compute_owner_billing_balance')

    @api.depends('owner_bill_ids.balance', 'owner_bill_ids.state', 'owner_bill_ids.is_defaulter')
    def _compute_owner_billing_balance(self):
        for partner in self:
            open_bills = partner.owner_bill_ids.filtered(lambda b: b.state == 'issued')
            partner.owner_billing_balance = sum(open_bills.mapped('balance'))
            partner.owner_billing_is_defaulter = any(open_bills.mapped('is_defaulter'))
