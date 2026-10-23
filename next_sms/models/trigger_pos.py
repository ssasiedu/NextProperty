# -*- coding: utf-8 -*-
from odoo import api, models


class NextQrOrder(models.Model):
    _inherit = 'next.qr.order'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        Template = self.env['next.sms.template']
        for rec in records:
            Template.send_trigger('qr_order_received', rec.reservation_id.partner_id,
                                   property_id=rec.room_id.property_id.id,
                                   placeholders={'room_number': rec.room_id.name, 'amount': rec.amount_total},
                                   related_record=rec)
        return records

    def action_mark_ready(self):
        res = super().action_mark_ready()
        Template = self.env['next.sms.template']
        for rec in self:
            Template.send_trigger('qr_order_ready', rec.reservation_id.partner_id,
                                   property_id=rec.room_id.property_id.id,
                                   placeholders={'room_number': rec.room_id.name}, related_record=rec)
        return res
