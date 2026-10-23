# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _find_or_create_ota_guest(self, payload):
        """Resolves (or creates) the guest partner for an incoming OTA
        booking payload, matched by email/phone when possible."""
        email = payload.get('guest_email')
        name = payload.get('guest_name', 'OTA Guest')
        partner = None
        if email:
            partner = self.search([('email', '=', email)], limit=1)
        if not partner:
            partner = self.create({
                'name': name, 'email': email, 'phone': payload.get('guest_phone'),
            })
        return partner.id


class NextReservation(models.Model):
    """Routes EVERY reservation - direct website, walk-in, or OTA - through
    the same availability-ledger locking, so the zero-double-booking
    guarantee is channel-agnostic. This overrides next_base's ORM-level
    constraint-only guard with the real concurrency-safe mechanism."""
    _inherit = 'next.reservation'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        Ledger = self.env['next.availability.ledger']
        for rec in records:
            if rec.room_ids and rec.state != 'cancelled':
                Ledger.reserve_nights(
                    rec.room_ids.ids, rec.date_from.date(), rec.date_to.date(),
                    reservation_id=rec.id)
        return records

    def action_cancel(self):
        res = super().action_cancel()
        Ledger = self.env['next.availability.ledger']
        for rec in self:
            Ledger.release_nights(rec.room_ids.ids, rec.date_from.date(), rec.date_to.date())
        return res
