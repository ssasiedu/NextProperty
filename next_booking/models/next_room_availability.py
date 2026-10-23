# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextRoomType(models.Model):
    """Extends next.room.type with the server-side availability search used
    by the booking website. This is the single source of truth for 'is this
    room type bookable for these dates/occupancy' - the website controller
    never computes availability itself, it only calls this method."""
    _inherit = 'next.room.type'

    @api.model
    def search_available(self, property_id, date_from, date_to, adults=1, children=0, room_count=1):
        """Returns a recordset of next.room.type that:
          - belong to `property_id` (if given)
          - have capacity >= adults/children for at least one room
          - have at least `room_count` rooms with NO conflicting reservation,
            NO maintenance block (grey_blocked / next.maintenance.request open),
            and NO channel-manager hold for the given date range.

        next_channel_manager overrides/augments the per-room conflict check
        (`next.room.is_blocked_for_booking` and its own availability ledger)
        to add OTA holds; this method already calls that hook point.
        """
        domain = [('active', '=', True)]
        if property_id:
            domain.append(('property_id', '=', property_id))
        domain += [('max_adults', '>=', adults), ('max_children', '>=', children)]

        room_types = self.search(domain)
        available = self.browse()
        for rt in room_types:
            free_rooms = rt.room_ids.filtered(
                lambda r: r.active and not r.is_blocked_for_booking(date_from, date_to)
            )
            if len(free_rooms) >= room_count:
                available |= rt
        return available

    def get_available_rooms(self, date_from, date_to):
        """Rooms of this room type free for the given range - used once the
        guest has picked a room type, to let them pick a specific room (or
        auto-assign the first one)."""
        self.ensure_one()
        return self.room_ids.filtered(
            lambda r: r.active and not r.is_blocked_for_booking(date_from, date_to)
        )

    def price_for_stay(self, date_from, date_to, adults=1, children=0):
        """Simple nightly-rate pricing: weekend_price (if set) on
        Fri/Sat nights, list_price otherwise, plus extra-occupancy
        surcharges beyond base_occupancy. Channel managers / promo
        pricing can override this method."""
        self.ensure_one()
        nights = (date_to.date() - date_from.date()).days
        total = 0.0
        cursor = date_from
        for _ in range(max(nights, 0)):
            is_weekend = cursor.weekday() in (4, 5)  # Friday, Saturday
            nightly = self.weekend_price if (is_weekend and self.weekend_price) else self.list_price
            total += nightly
            cursor = fields.Datetime.add(cursor, days=1)

        extra_occupants = max((adults + children) - self.base_occupancy, 0)
        if extra_occupants and adults > self.base_occupancy:
            total += self.extra_adult_price * nights * min(extra_occupants, adults - self.base_occupancy)
        if children and self.extra_child_price:
            total += self.extra_child_price * nights * children
        return total
