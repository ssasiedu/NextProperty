# next_pos_integration

POS ↔ folio bridge and per-room QR self-ordering.

## Depends on
`next_base`, `point_of_sale`.

## External Python dependency
`qrcode` (`pip install "qrcode[pil]"`) — used by `next.room.action_generate_qr_code()`.

## Provides
- `pos.order` extension: a `next_reservation_id` field; when set, paying the
  POS order posts it as a `next.folio.line` (via `_next_post_to_folio`)
  instead of becoming a standalone invoice.
- `pos.config.next_property_id` to link a POS point of sale to a property.
- `next.room.action_generate_qr_code()` — generates and stores a QR image
  per room linking to `/qr-order/<room_id>/<token>`.
- The QR self-order flow: a public, token-gated mobile page
  (`controllers/qr_order.py`) where guests order food/drink/services. Orders
  post directly to the guest's folio (`next.qr.order` → `next.folio.line`)
  and create a draft `pos.order` on the active POS session so kitchen/
  service staff see it on their normal order tickets.

## Notes
- `next.room._next_qr_token()` uses a simple deterministic hash for this
  scaffold. Production deployments should replace it with a signed,
  expiring token (e.g. `itsdangerous`).
- Final checkout invoice = room charges + all POS/QR lines + repair/damage
  charges, assembled by `next.folio.action_create_invoice()` in `next_base`.
