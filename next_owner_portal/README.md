# next_owner_portal

Owner-facing dashboard, financials, and property-viewing scheduling.

## Depends on
`next_base`, `next_sms`, `calendar`, `portal`.

## Non-negotiable constraint enforced here
**Property Owners never see system-computed net revenue.** The Owner Portal
(`/my/owner/net-revenue`) and the Settlement PDF query **only**
`next.owner.net.revenue` records with `state = 'published'`. The internal
BI dashboard (`next.bi.reservation.report`, an SQL view) and
`next.room.compute_internal_net_income()` are manager/accountant-only
(enforced by `ir.model.access.csv` + the record rule in
`security/next_owner_portal_security.xml`) and are never queried by any
owner-facing view or controller.

## Provides
- **BI Dashboard** (internal): gross revenue trend, occupancy rate, booking
  source split, cancellation stats, ADR, RevPAR — `next.bi.reservation.report`.
- **`next.owner.net.revenue`**: manually entered, `unique(property_id,
  room_id, period_month, period_year, state)`. `action_publish()` locks it;
  further changes to a published record require `action_create_revision()`,
  which creates a linked draft copy (`supersedes_id`) — publishing the
  revision flips the original to `superseded`. `write()` raises if anyone
  tries to edit a published record's figures directly — there is no silent
  edit path.
- **`next.room.expense`** + `next.room.compute_internal_net_income()`:
  internal revenue-minus-expenses per room/period, used by
  `action_generate_settlement_statement()` to reconcile against the
  published figure (posts a warning message if they diverge) before
  rendering the Settlement PDF (`report/`).
- **`next.property.viewing`**: slot-based, creates a real `calendar.event`
  on confirm; can block the room from guest bookings
  (`requires_room_block`) for the slot.
- **Live room status for owners**: `/my/owner/rooms`, scoped to
  `partner.owned_room_ids` only.

## SMS triggers wired here (calling `next_sms` directly — see its README)
`owner_net_revenue_published`, `owner_viewing_requested`,
`owner_viewing_confirmed`, `owner_room_status_change`.
