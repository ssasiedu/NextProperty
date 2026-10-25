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
- **Worker self-service portal** (`/my/worker/housekeeping`): `group_next_
  housekeeping` is PORTAL-tier, not a full internal user (see next_base's
  security groups) - a plain room attendant never touches the backend
  Kanban, just this page: task counts (total/not started/in progress/
  complete), optional date-range filter, and a Start/Complete button per
  task, each scoped to `assigned_to == current user` and run via `sudo()`
  after that check. `group_next_housekeeping_supervisor` additionally
  implies `base.group_user`, so supervisors keep full backend access.
