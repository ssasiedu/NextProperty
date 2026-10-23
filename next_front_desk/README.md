# next_front_desk

Front desk operations: room dashboard, check-in/out, inventory reconciliation.

## Depends on
`next_base`.

## Provides
- Front Desk Dashboard: Kanban (grouped by room `status`, drag-and-drop
  between columns to reassign) + a Gantt-style Room Schedule view of
  reservations against rooms.
- One-click check-in; one-click check-out is **hard-blocked** behind the
  mandatory `next.checkout.reconciliation.wizard`.
- `next.guest.inventory.item` — items issued per stay (keys, remote,
  minibar, towels, equipment), auto-seeded with a key + remote on check-in.
- The reconciliation wizard: staff confirm quantity returned for every
  issued item; any shortfall becomes a `damage` folio line automatically,
  and only then is the reservation allowed to transition to `checked_out`.

## Non-negotiable constraint enforced here
`next.reservation.action_check_out()` raises unless
`checkout_reconciled = True`, which only the wizard's confirm action sets.
There is no UI path to checkout that skips the wizard.
