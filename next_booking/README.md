# next_booking

Website booking flow and Guest Portal.

## Depends on
`next_base`, `website`, `portal`, `payment`.

## Provides
- A strict, route-enforced booking flow: `/book/property` → `/book/dates` →
  `/book/occupancy` → `/book/availability` → `/book/select/<room_type_id>` →
  `/book/confirm`. Each step validates the previous step's parameters are
  present and redirects back if not.
- Server-side availability search (`next.room.type.search_available`,
  `get_available_rooms`, `price_for_stay`) — the single source of truth the
  website controller queries; it never computes availability itself.
- Guest Portal pages under `/my/bookings` (history, detail, folio + PDF) and
  `/my/service-requests` (fault/room-service/general requests with a
  guest-visible status).
- `next.service.request` model.

## Notes / assumptions
- Payment: `/book/confirm` creates the reservation in draft/confirmed state
  and is the integration point for Odoo's standard `payment` flow; wire your
  acquirer of choice there. No specific payment provider was specified in
  the brief, so this ships provider-agnostic.
- `next_maintenance` (installed later) extends `next.service.request` to
  auto-escalate `fault` requests into a `maintenance.request` ticket on
  acknowledgement.
