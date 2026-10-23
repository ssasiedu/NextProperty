# -*- coding: utf-8 -*-
from odoo import models


class NextServiceRequest(models.Model):
    _inherit = 'next.service.request'

    def action_acknowledge(self):
        """Fault reports are escalated into a next.maintenance.request
        (an Odoo maintenance.request) when acknowledged, so maintenance
        officers work from their normal queue; other request types are
        just acknowledged in place."""
        res = super().action_acknowledge()
        for rec in self:
            if rec.request_type == 'fault' and not rec.maintenance_request_id:
                room = rec.reservation_id.room_ids[:1]
                ticket = self.env['maintenance.request'].create({
                    'name': rec.name,
                    'description': rec.description,
                    'next_room_id': room.id,
                    'raised_by_type': 'guest',
                    'service_request_id': rec.id,
                })
                rec.maintenance_request_id = ticket.id
        return res
