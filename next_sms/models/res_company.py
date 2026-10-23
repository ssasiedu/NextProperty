# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    next_sms_provider_ids = fields.One2many('next.sms.provider', 'company_id', string='SMS Providers')
