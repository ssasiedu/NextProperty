# next_housekeeping

Housekeeping task management.

## Depends on
`next_base`, `portal`.

## Provides
- `next.housekeeping.task`: `not_started → in_progress → inspected → complete`.
- Auto-creates a `checkout_clean` task for every room on
  `next.reservation.action_check_out()`.
- Daily cron (`_cron_create_routine_tasks`) creates a `routine` task for
  every currently occupied room that doesn't already have one open today.
- Hourly cron (`_cron_flag_overdue_tasks`) flags/logs overdue tasks
  (`next_sms` hooks into this cron to notify the supervisor).
- Supervisor Kanban dashboard (grouped by state) to assign/reassign.
- On `action_complete()`, flips the room from `red_pending_checkout` to
  `green_ready` automatically.
- **Worker self-service portal** (`/my/worker/housekeeping`): a room
  attendant only ever needs this page, never the backend Kanban - task
  counts (total/not started/in progress/complete), optional date-range
  filter, and a Start/Complete button per task, each scoped to
  `assigned_to == current user` and run via `sudo()` after that check.
  `group_next_housekeeping` itself carries no Odoo Role (Internal/Portal)
  - give a plain attendant **portal access** when creating their account
  (Settings > Users > grant Portal Access) and tick this group; give a
  **Housekeeping Supervisor** a normal Internal User account and tick
  `group_next_housekeeping_supervisor` instead, which implies this group
  plus `base.group_user` for full backend access. (Forcing a Role via
  group implication here would conflict with Supervisor needing the
  opposite role on the same user chain - Odoo treats Internal/Portal as
  mutually exclusive.)
