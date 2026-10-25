# next_maintenance

Repair/fault request management, built on Odoo's native Maintenance app.

## Depends on
`next_base`, `next_booking` (for guest service-request escalation),
`maintenance`, `portal`.

## Provides
- Extends `maintenance.request` (does **not** reinvent a parallel model)
  with: `next_room_id`, `next_property_id`, `raised_by_type`
  (guest/housekeeping/front_desk/staff), `assigned_officer_id`,
  `auto_block_room`, and the state machine `new → assigned → in_progress →
  resolved → verified`.
- While open (and `auto_block_room` is set), the room is set to
  `grey_blocked`, which `next.room.is_blocked_for_booking()` (in
  `next_base`) already excludes from availability — no separate blocking
  logic needed.
- `action_verify()` clears the room block and, if the ticket originated
  from a guest `next.service.request`, resolves that request too.
- Escalation: `next.service.request.action_acknowledge()` is extended so a
  `fault` request automatically creates a linked `maintenance.request`
  ticket with `raised_by_type = 'guest'`.
- **Worker self-service portal** (`/my/worker/maintenance`): same shape and
  same reasoning as next_housekeeping's - `group_next_maintenance_officer`
  carries no Odoo Role by itself (give a technician portal access when
  creating their account); `group_next_maintenance_supervisor` implies
  this group plus `base.group_user`, for a normal Internal User account
  that needs the real backend.
