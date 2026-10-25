# next_base

Core data model and security foundation for NEXT Property Management.

## Depends on
`base`, `mail`, `portal` (core Odoo only — this module has no dependency on
any other `next_*` module).

## Provides
- `next.property`, `next.room.type`, `next.room`, `next.reservation`,
  `next.folio` (+ `next.folio.line`, `next.folio.payment`).
- `res.partner` extension: `is_property_owner`, `owned_property_ids`,
  `owned_room_ids`, `sms_opt_in`, `email_opt_in`.
- Deposit / advance payment on `next.reservation`: `deposit_required` +
  `deposit_amount`; `action_confirm()` refuses to confirm a reservation that
  requires one until `action_record_deposit_payment()` has been called.
  That call posts a `next.folio.payment` (type `deposit`) on the folio, so
  `next.folio.amount_paid`/`amount_due` - and the printed final bill - show
  it as money already received, not just a flag on the reservation.
- Security groups: Front Desk Staff, Housekeeping Staff/Supervisor,
  Maintenance Officer, Property Owner, Accountant, Hotel Manager/Admin
  (Guest reuses Odoo's built-in Portal group).
- Record rules scoping Property Owners to their own rooms/properties/
  reservations/folios.
- The room `status` state machine (blue/yellow/red/green/grey) that every
  other module's dashboards read and write.

Every other `next_*` module depends on this one, directly or transitively.
