# -*- coding: utf-8 -*-
from odoo import api, models


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        Template = self.env['next.sms.template']
        for rec in records:
            if rec.assigned_officer_id:
                Template.send_trigger('maintenance_new_ticket', rec.assigned_officer_id.partner_id,
                                       property_id=rec.next_property_id.id,
                                       placeholders={'room_number': rec.next_room_id.name, 'guest_name': rec.name},
                                       related_record=rec)
        return records

    def _next_notify_status_update(self):
        Template = self.env['next.sms.template']
        for rec in self:
            recipients = self.env['res.partner']
            if rec.service_request_id:
                recipients |= rec.service_request_id.partner_id
            if rec.next_room_id.owner_id:
                recipients |= rec.next_room_id.owner_id
            for partner in recipients:
                Template.send_trigger('maintenance_status_update', partner,
                                       property_id=rec.next_property_id.id,
                                       placeholders={'room_number': rec.next_room_id.name, 'status': rec.next_state},
                                       related_record=rec)

    def action_start_progress(self):
        res = super().action_start_progress()
        self._next_notify_status_update()
        return res

    def action_resolve(self):
        res = super().action_resolve()
        self._next_notify_status_update()
        return res
