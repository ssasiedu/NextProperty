# -*- coding: utf-8 -*-
from odoo import models


class NextRoom(models.Model):
    _inherit = 'next.room'

    def is_blocked_for_booking(self, date_from, date_to):
        """Augments next_base's check with the availability ledger, so
        display/search-time availability (website search, portal) agrees
        with the concurrency-safe source of truth used at booking time."""
        if super().is_blocked_for_booking(date_from, date_to):
            return True
        Ledger = self.env['next.availability.ledger']
        held = Ledger.search_count([
            ('room_id', '=', self.id),
            ('date', '>=', date_from.date() if hasattr(date_from, 'date') else date_from),
            ('date', '<', date_to.date() if hasattr(date_to, 'date') else date_to),
            '|', ('reservation_id', '!=', False), ('ota_hold_channel', '!=', False),
        ])
        return bool(held)
