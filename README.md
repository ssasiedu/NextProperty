# NEXT Property Management — Odoo v19 Smart Hotel Management Suite

Nine interdependent custom modules, prefixed `next_`/`next.`, extending
native Odoo apps (Website, POS, Maintenance, Calendar, Accounting, Portal)
rather than reinventing them.

## Modules

| # | Module | Summary |
|---|---|---|
| 1 | `next_base` | Core models, security groups, record rules |
| 2 | `next_booking` | Website booking flow + Guest Portal |
| 3 | `next_front_desk` | Room dashboard, check-in/out, inventory reconciliation |
| 4 | `next_pos_integration` | POS↔folio bridge, QR self-ordering |
| 5 | `next_housekeeping` | Housekeeping tasks, room-status automation |
| 6 | `next_maintenance` | Repair/fault requests (extends `maintenance`) |
| 7 | `next_sms` | Hubtel SMS, async dispatch, triggers wired across 2–6 |
| 8 | `next_owner_portal` | Owner BI, manual net revenue, expenses, viewings |
| 9 | `next_channel_manager` | OTA sync, zero-double-booking availability ledger |

Each module has its own `README.md` with more detail; start there for
anything module-specific.

## Install order

Install in this order (matches each module's `depends`, so Odoo's own
dependency resolution will enforce it regardless, but doing it in order
makes debugging easier if something's missing):

```
next_base
next_booking
next_front_desk
next_pos_integration
next_housekeeping
next_maintenance
next_sms
next_owner_portal
next_channel_manager
```

## Deploying to odoo.sh / GitHub

1. Each top-level folder here (`next_base/`, `next_booking/`, ...) is a
   complete, independent Odoo addon — copy all nine into your repo's addons
   path (e.g. the repo root, if odoo.sh is configured to scan it, or a
   dedicated `addons/` folder referenced in your `odoo.sh`/`addons_path`
   config).
2. Python dependency: `next_pos_integration` needs the `qrcode` package
   (`external_dependencies` in its manifest; odoo.sh installs this
   automatically from the manifest, no extra step needed there — for a
   manual server, `pip install "qrcode[pil]"`).
3. Optional: install OCA `queue_job` for true job-queue SMS dispatch;
   `next_sms` auto-detects it and falls back to its own cron-based queue
   if it's absent — no configuration needed either way.
4. After install, configure in this order: Properties/Room Types/Rooms
   (`next_base`) → an SMS Provider (`next_sms`, Settings → NEXT Property
   Mgmt → SMS → Providers) → OTA Channels if used (`next_channel_manager`).

## Assumptions made (stated explicitly, per the brief)

- **Edition**: Community-compatible throughout. No Enterprise-only field or
  view type is required (Gantt/Calendar/Kanban/Pivot/Graph are all
  Community). If you're on Enterprise, nothing here needs to change, but
  you could swap the hand-rolled dashboards for Spreadsheet Dashboards if
  preferred.
- **Channel-manager API**: no specific OTA API was named, so
  `next_channel_manager` ships pluggable sandbox adapters for Airbnb,
  Expedia and Booking.com that log their payloads. The adapter interface
  (`BaseOtaAdapter`) is the integration point for real credentials later —
  see that module's README.
- **Hubtel credentials/sender ID format**: left as empty configuration
  fields on `next.sms.provider`; the adapter uses Hubtel's documented
  quick-SMS GET endpoint shape as a reasonable default pending your
  account's exact contract.
- **Payment acquirer**: `next_booking`'s checkout step creates the
  reservation and is the integration point for Odoo's standard `payment`
  flow; no specific acquirer was named, so none is hard-wired.
- **Tax jurisdiction**: left to your Odoo Accounting/fiscal position
  configuration; no next_* model hard-codes a tax rate or jurisdiction.
- **Async SMS**: implemented against OCA `queue_job` when present, with a
  self-contained cron-based fallback otherwise, so the suite doesn't have a
  hard dependency on a module outside this repo.

## What was validated before delivery

Every `.py` file in all nine modules compiles cleanly
(`python3 -m py_compile`), and every `.xml` file is well-formed XML. This
doesn't substitute for installing against a real Odoo 19 database (module
dependency loading, view inheritance targets, and field-level ORM
constraints can only be fully verified by Odoo itself at install time), but
it does rule out the most common packaging errors before you deploy.
