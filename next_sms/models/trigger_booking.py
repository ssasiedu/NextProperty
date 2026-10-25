# -*- coding: utf-8 -*-
from odoo import models


def _reservation_placeholders(reservation):
    return {
        'guest_name': reservation.partner_id.name,
        'room_number': ', '.join(reservation.room_ids.mapped('name')) or 'TBD',
        'date_from': reservation.date_from and reservation.date_from.strftime('%Y-%m-%d') or '',
        'date_to': reservation.date_to and reservation.date_to.strftime('%Y-%m-%d') or '',
        'amount': reservation.folio_id.amount_total,
        'property_name': reservation.property_id.name,
    }


class NextReservation(models.Model):
    _inherit = 'next.reservation'

    def action_confirm(self):
        res = super().action_confirm()
        Template = self.env['next.sms.template']
        for rec in self:
            Template.send_trigger('booking_confirmation', rec.partner_id,
                                   property_id=rec.property_id.id,
                                   placeholders=_reservation_placeholders(rec), related_record=rec)
        return res

    def action_record_deposit_payment(self, reference=None):
        res = super().action_record_deposit_payment(reference=reference)
        Template = self.env['next.sms.template']
        for rec in self:
            if rec.deposit_paid:
                Template.send_trigger('booking_deposit_received', rec.partner_id,
                                       property_id=rec.property_id.id,
                                       placeholders=dict(_reservation_placeholders(rec),
                                                          deposit_amount=rec.deposit_amount),
                                       related_record=rec)
        return res

    def action_cancel(self):
        res = super().action_cancel()
        Template = self.env['next.sms.template']
        for rec in self:
            Template.send_trigger('booking_cancellation', rec.partner_id,
                                   property_id=rec.property_id.id,
                                   placeholders=_reservation_placeholders(rec), related_record=rec)
        return res

    def _cron_send_checkin_reminders(self):
        """Daily cron (see data/next_sms_cron.xml): sends the 24h pre
        check-in reminder to every confirmed reservation checking in
        tomorrow."""
        from odoo import fields
        tomorrow_start = fields.Datetime.add(fields.Datetime.now(), hours=23)
        tomorrow_end = fields.Datetime.add(fields.Datetime.now(), hours=25)
        reservations = self.search([
            ('state', '=', 'confirmed'),
            ('date_from', '>=', tomorrow_start), ('date_from', '<=', tomorrow_end),
        ])
        Template = self.env['next.sms.template']
        for rec in reservations:
            Template.send_trigger('booking_reminder', rec.partner_id,
                                   property_id=rec.property_id.id,
                                   placeholders=_reservation_placeholders(rec), related_record=rec)


class NextServiceRequest(models.Model):
    _inherit = 'next.service.request'
    # Guest service requests (fault/room-service/general) are not in the
    # trigger table themselves; QR orders and maintenance tickets (their
    # usual escalation target) carry their own triggers below/elsewhere.
