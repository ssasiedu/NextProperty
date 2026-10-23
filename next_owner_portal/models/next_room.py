# -*- coding: utf-8 -*-
from odoo import models


class NextRoom(models.Model):
    _inherit = 'next.room'

    def write(self, vals):
        old_status_by_id = {r.id: r.status for r in self} if 'status' in vals else {}
        res = super().write(vals)
        if 'status' in vals:
            Template = self.env['next.sms.template']
            for room in self:
                old_status = old_status_by_id.get(room.id)
                if old_status and old_status != room.status and room.owner_id:
                    # Per-property togglable via the template's active/property_id
                    # fields in next_sms - no extra flag needed here.
                    Template.send_trigger('owner_room_status_change', room.owner_id,
                                           property_id=room.property_id.id,
                                           placeholders={
                                               'room_number': room.name,
                                               'property_name': room.property_id.name,
                                               'status': room.status,
                                           }, related_record=room)
        return res
