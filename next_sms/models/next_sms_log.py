# -*- coding: utf-8 -*-
from odoo import fields, models


class NextSmsLog(models.Model):
    _name = 'next.sms.log'
    _description = 'SMS Log'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', required=True, index=True)
    property_id = fields.Many2one('next.property')
    trigger_code = fields.Char(index=True)
    to_number = fields.Char(required=True)
    message = fields.Text(required=True)

    status = fields.Selection([
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], default='queued', required=True, index=True)

    provider_message_id = fields.Char(index=True)
    error_message = fields.Char()
    cost = fields.Float(help='Cost of this message, if returned/known by the provider, for usage/cost tracking.')

    sent_date = fields.Datetime(readonly=True)
    delivered_date = fields.Datetime(readonly=True)

    related_model = fields.Char()
    related_res_id = fields.Integer()
