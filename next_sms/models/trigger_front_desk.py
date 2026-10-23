# -*- coding: utf-8 -*-
from odoo import models


class NextReservation(models.Model):
    _inherit = 'next.reservation'

    def action_check_in(self):
        res = super().action_check_in()
        Template = self.env['next.sms.template']
        for rec in self:
            Template.send_trigger('checkin_complete', rec.partner_id,
                                   property_id=rec.property_id.id,
                                   placeholders={
                                       'guest_name': rec.partner_id.name,
                                       'room_number': ', '.join(rec.room_ids.mapped('name')),
                                       'property_name': rec.property_id.name,
                                   }, related_record=rec)
        return res

    def action_check_out(self):
        res = super().action_check_out()
        Template = self.env['next.sms.template']
        for rec in self:
            Template.send_trigger('checkout_complete', rec.partner_id,
                                   property_id=rec.property_id.id,
                                   placeholders={
                                       'guest_name': rec.partner_id.name,
                                       'room_number': ', '.join(rec.room_ids.mapped('name')),
                                       'amount': rec.folio_id.amount_total,
                                   }, related_record=rec)
        return res


class NextCheckoutReconciliationWizard(models.TransientModel):
    _inherit = 'next.checkout.reconciliation.wizard'

    def action_confirm(self):
        total_discrepancy_before = sum(self.line_ids.mapped('inventory_item_id.discrepancy_charge'))
        res = super().action_confirm()
        if total_discrepancy_before:
            reservation = self.reservation_id
            supervisor_group = self.env.ref('next_base.group_next_housekeeping_supervisor')
            supervisors = self.env['res.users'].search([('groups_id', 'in', supervisor_group.id)])
            Template = self.env['next.sms.template']
            for supervisor in supervisors.mapped('partner_id'):
                Template.send_trigger('checkout_discrepancy', supervisor,
                                       property_id=reservation.property_id.id,
                                       placeholders={
                                           'guest_name': reservation.partner_id.name,
                                           'room_number': ', '.join(reservation.room_ids.mapped('name')),
                                           'amount': total_discrepancy_before,
                                       }, related_record=reservation)
        return res
