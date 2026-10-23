# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class NextAvailabilityLedger(models.Model):
    """One row per (room, date). `held_by` is non-null while a reservation
    occupies that night. This is the single source of truth for availability
    across ALL channels (website, walk-in, OTA) - next.room.is_blocked_for_booking
    (next_base) and next.room.type.search_available (next_booking) are
    advisory/display helpers; THIS model is what actually prevents a double
    booking, via `reserve_nights()`'s row-level locking.

    Design: rather than locking next.reservation rows (which don't exist yet
    for a brand-new booking and can't be locked pre-emptively), we lock the
    ledger rows for the exact (room, date) tuples being booked. Postgres
    `SELECT ... FOR UPDATE` on those rows means two concurrent requests for
    the same room/night can never both succeed - the second blocks until the
    first commits or rolls back, then sees the row already held and raises.
    """
    _name = 'next.availability.ledger'
    _description = 'Availability Ledger'
    _order = 'date, room_id'

    room_id = fields.Many2one('next.room', required=True, index=True)
    date = fields.Date(required=True, index=True)
    reservation_id = fields.Many2one('next.reservation', string='Held By', index=True)
    ota_hold_channel = fields.Char(help='Set instead of reservation_id for a temporary OTA-side hold '
                                         '(e.g. while a guest is completing payment on the OTA).')

    _room_date_uniq = models.Constraint(
        'unique(room_id, date)',
        'One ledger row per room per night.',
    )

    @api.model
    def ensure_rows(self, room_ids, date_from, date_to):
        """Idempotently creates the (room, date) rows needed for a range,
        without locking anything - call this once up front (e.g. a nightly
        cron extending the horizon), never inside the locking transaction
        below, to avoid creating rows under lock."""
        existing = set(self.search([
            ('room_id', 'in', room_ids), ('date', '>=', date_from), ('date', '<', date_to),
        ]).mapped(lambda r: (r.room_id.id, r.date)))
        to_create = []
        cursor = date_from
        while cursor < date_to:
            for room_id in room_ids:
                if (room_id, cursor) not in existing:
                    to_create.append({'room_id': room_id, 'date': cursor})
            cursor = fields.Date.add(cursor, days=1)
        if to_create:
            self.create(to_create)

    def reserve_nights(self, room_ids, date_from, date_to, reservation_id=None, ota_channel=None):
        """The concurrency-safe entry point. Locks the exact rows for
        (room_ids x [date_from, date_to)) with FOR UPDATE, checks none are
        already held, then marks them held - all inside the caller's
        transaction, so it either fully succeeds or fully rolls back.

        Raises UserError on any conflict (double-booking attempt), which the
        caller (website checkout, walk-in creation, OTA webhook handler)
        should surface as "sorry, that room just became unavailable".
        """
        self.ensure_rows(room_ids, date_from, date_to)
        dates = []
        cursor = date_from
        while cursor < date_to:
            dates.append(cursor)
            cursor = fields.Date.add(cursor, days=1)

        # Lock in a stable order (room_id, date) to avoid deadlocks between
        # two concurrent bookings that both touch overlapping room sets.
        self.env.cr.execute(
            """SELECT id, reservation_id, ota_hold_channel FROM next_availability_ledger
               WHERE room_id = ANY(%s) AND date = ANY(%s)
               ORDER BY room_id, date
               FOR UPDATE""",
            (room_ids, dates),
        )
        rows = self.env.cr.fetchall()
        held = [r for r in rows if r[1] or r[2]]
        if held:
            raise UserError(
                'One or more selected rooms/dates were just booked by another channel. '
                'Please choose different rooms or dates.')

        row_ids = [r[0] for r in rows]
        vals = {'reservation_id': reservation_id} if reservation_id else {'ota_hold_channel': ota_channel}
        self.browse(row_ids).write(vals)
        return True

    def release_nights(self, room_ids, date_from, date_to):
        """Releases a hold (cancellation). No locking needed to release -
        only acquiring needs the race-condition guard."""
        rows = self.search([
            ('room_id', 'in', room_ids), ('date', '>=', date_from), ('date', '<', date_to),
        ])
        rows.write({'reservation_id': False, 'ota_hold_channel': False})
