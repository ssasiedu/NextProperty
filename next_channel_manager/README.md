# next_channel_manager

OTA synchronization with a concurrency-safe, zero-double-booking availability ledger.

## Depends on
`next_base`, `next_sms`.

## The zero-double-booking guarantee
`next.availability.ledger` has one row per `(room_id, date)`, unique-
constrained. **Every** reservation — direct website, walk-in, or OTA — goes
through `next.availability.ledger.reserve_nights()`, which:
1. Locks the exact rows for the requested `(rooms × date range)` with
   `SELECT ... FOR UPDATE`, in a stable `(room_id, date)` order (avoids
   deadlocks between two overlapping concurrent bookings).
2. Checks none of the locked rows are already held
   (`reservation_id` or `ota_hold_channel` set).
3. If clear, marks them held, inside the same DB transaction as the
   reservation `create()` — so a conflict raises `UserError` and the whole
   transaction (ledger + reservation) rolls back together.

This is wired into `next.reservation.create()`/`action_cancel()`
(`models/next_reservation.py`) and into
`next.ota.channel.process_incoming_booking()`, so website, walk-in and OTA
bookings are indistinguishable to the ledger — none can race past another.

`next.room.is_blocked_for_booking()` is extended to also consult the ledger,
so search-time availability (website, portal) agrees with booking-time
enforcement.

## OTA sync
- `next.ota.channel` holds per-property, per-OTA config
  (Airbnb/Expedia/Booking.com) and resolves a pluggable adapter
  (`models/ota_adapters.py`) implementing `push_availability` / `push_rates`.
- A 15-minute cron (`ir_cron_next_channel_sync`) pushes the ledger's current
  availability and current room-type rates to every active channel.
- Incoming OTA bookings go through `process_incoming_booking()`, which
  resolves/creates the guest partner, creates the reservation (which itself
  locks the ledger), confirms it, and fires the
  `channel_ota_booking_received` SMS trigger.

## Assumption
No specific channel-manager API was named in the brief, so the three
adapters ship as sandbox/logging implementations
(`ADAPTER_REGISTRY` in `ota_adapters.py`) rather than calling a real
Airbnb/Expedia/Booking.com endpoint. Point `BaseOtaAdapter._http_post` at
the real endpoint and credentials once you have them — no other file needs
to change.
