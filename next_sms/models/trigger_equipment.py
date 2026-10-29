# -*- coding: utf-8 -*-
from odoo import models


class MaintenanceEquipment(models.Model):
    """Wires next_maintenance's equipment notification hooks
    (maintenance.equipment._notify_preventive_*) to actually send SMS/email,
    alongside the chatter message + activity those hooks already guarantee
    on their own - same "extend the hook, don't make the other module
    depend on next_sms" pattern as trigger_maintenance.py."""
    _inherit = 'maintenance.equipment'

    def _send_equipment_trigger(self, trigger_code, placeholders):
        Template = self.env['next.sms.template']
        for eq in self:
            if not eq.maintenance_supervisor_id:
                continue
            Template.send_trigger(
                trigger_code, eq.maintenance_supervisor_id.partner_id,
                property_id=eq.next_property_id.id,
                placeholders=dict({
                    'equipment_name': eq.name,
                    'room_number': eq.next_room_id.name or 'Property-wide',
                    'due_date': eq.next_maintenance_date or '',
                }, **placeholders),
                related_record=eq)

    def _notify_preventive_due_soon(self):
        res = super()._notify_preventive_due_soon()
        self._send_equipment_trigger('equipment_maintenance_due_soon', {'amount': ''})
        return res

    def _notify_preventive_overdue(self):
        res = super()._notify_preventive_overdue()
        for eq in self:
            eq._send_equipment_trigger('equipment_maintenance_overdue', {'amount': eq.overdue_penalty_amount})
        return res

    def _notify_preventive_completed(self, cost):
        res = super()._notify_preventive_completed(cost)
        self._send_equipment_trigger('equipment_maintenance_completed', {'amount': cost})
        return res
