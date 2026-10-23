# next_sms

Provider-abstracted, asynchronous SMS dispatch (Hubtel), wired across the suite.

## Depends on
`next_base`, `next_booking`, `next_front_desk`, `next_housekeeping`,
`next_maintenance`, `next_pos_integration`.
(`next_owner_portal` and `next_channel_manager` install *after* this module
and call back into its API directly — see "Retrofit" below.)

## Core API
```python
self.env['next.sms.template'].send_trigger(
    'booking_confirmation', partner,
    property_id=some_property.id,
    placeholders={'guest_name': ..., 'room_number': ..., ...},
    related_record=reservation,
)
```
This single method: resolves the enabled template for
`(trigger_code, property)`, checks `partner.sms_opt_in`, renders `{placeholder}`
tokens, writes a `next.sms.log` row (`status='queued'`), and enqueues actual
delivery — it never blocks the caller on network I/O.

## Models
- `next.sms.provider` — Hubtel `client_id`/`client_secret`/`sender_id`/
  `callback_url`, per company/property. `provider_type` is a selection field
  so a second provider is a new `_send_via_<provider>()` branch, not a
  rewrite.
- `next.sms.template` — one per `(trigger_code, property|global)`, with the
  full trigger table from the spec as the `trigger_code` selection, and a
  per-template `active` toggle (= the per-property enable/disable switch).
- `next.sms.log` — every message, with `status`
  (queued/sent/delivered/failed), `provider_message_id`, `cost`.
- `next.sms.queue` — the async layer. If OCA `queue_job` is installed,
  dispatch goes through `with_delay()`; otherwise a 2-minute `ir.cron`
  fallback picks up `queued` rows. Either way, sending SMS never blocks a
  booking/checkout transaction.

## Delivery reports
`POST /next_sms/hubtel/delivery_report` updates the matching log by
`provider_message_id`.

## Technical dashboard
Menu **NEXT Property Mgmt → SMS → Dashboard** (pivot + graph on
`next.sms.log`) for delivery health and per-property/per-trigger cost
tracking.

## Trigger wiring
Implemented directly in this module (since it depends on the modules
below) by extending their models' action methods:

| Trigger | Wired in |
|---|---|
| booking_confirmation / booking_cancellation | `models/trigger_booking.py` → `next.reservation` |
| booking_reminder (24h cron) | `models/trigger_booking.py` → `_cron_send_checkin_reminders` |
| checkin_complete / checkout_complete | `models/trigger_front_desk.py` → `next.reservation` |
| checkout_discrepancy | `models/trigger_front_desk.py` → checkout wizard |
| qr_order_received / qr_order_ready | `models/trigger_pos.py` → `next.qr.order` |
| housekeeping_room_ready / task_overdue | `models/trigger_housekeeping.py` |
| maintenance_new_ticket / status_update | `models/trigger_maintenance.py` |

### Retrofit (per the build-order instruction)
`next_owner_portal` and `next_channel_manager` are built **after** this
module, so — rather than this module depending on modules that don't exist
yet when it installs — those two modules call
`self.env['next.sms.template'].send_trigger(...)` directly from their own
code for: `owner_net_revenue_published`, `owner_viewing_requested`,
`owner_viewing_confirmed`, `owner_room_status_change`, and
`channel_ota_booking_received`. `auth_otp` is provided as a template for use
by whatever 2FA mechanism you wire into portal login (optional per spec).

## Assumption
No Hubtel sender ID/credential format was supplied — `next.sms.provider`
ships with empty credential fields to fill in per deployment; the Hubtel
adapter uses Hubtel's documented quick-SMS GET endpoint shape as a
reasonable default. Swap `_send_via_hubtel` for the exact contract your
Hubtel account uses if it differs.
