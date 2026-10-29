{
    'name': 'NEXT Property Management - Channel Manager',
    'version': '19.0.1.1.0',
    'category': 'Industries/Hospitality',
    'summary': 'OTA synchronization with a concurrency-safe availability ledger (zero double-bookings)',
    'description': """
NEXT Property Management - Channel Manager
=============================================
* Integration layer (middleware/API client pattern) syncing room inventory
  and rates in real time with connected OTAs (Airbnb, Expedia, Booking.com).
* `next.availability.ledger`: one row per (room, date). Every reservation -
  website, POS/walk-in, or OTA - must atomically decrement this ledger using
  `SELECT ... FOR UPDATE` row-level locking, guaranteeing zero double-bookings
  across all channels regardless of which one originated the booking.
* OTA client adapters are pluggable (one Python class per channel) behind a
  common interface, so adding a new OTA means adding one adapter, not
  touching booking logic.

Assumption (stated per the brief, since no specific channel-manager API
credentials were given): this module ships with a provider-agnostic adapter
interface and a mock/sandbox adapter for Airbnb, Expedia and Booking.com so
the suite installs and runs end-to-end; wiring real OTA credentials/API
calls is a drop-in configuration + adapter implementation step.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'next_sms'],
    'data': [
        'security/ir.model.access.csv',
        'data/next_channel_manager_cron.xml',
        'views/next_availability_ledger_views.xml',
        'views/next_ota_channel_views.xml',
        'views/next_channel_manager_menus.xml',
    ],
    'installable': True,
    'application': False,
}
