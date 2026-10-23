{
    'name': 'NEXT Property Management - SMS (Hubtel)',
    'version': '19.0.1.0.0',
    'category': 'Industries/Hospitality',
    'summary': 'Provider-abstracted async SMS dispatch (Hubtel) wired across the NEXT suite',
    'description': """
NEXT Property Management - SMS
=================================
* `next.sms.provider` - Hubtel credentials (client_id, client_secret, sender_id,
  callback_url) configurable per company/property. Designed so another
  provider can be plugged in later via `_send_via_provider()`.
* `next.sms.template` - per trigger-event template with placeholders, with a
  per-template enable/disable toggle per property.
* `next.sms.log` - every outbound message logged with delivery status,
  updated via Hubtel's delivery-report callback endpoint.
* Asynchronous dispatch via OCA `queue_job` when installed, else a built-in
  `next.sms.queue` + cron fallback - either way, sending never blocks a
  booking/checkout transaction.
* Respects `res.partner.sms_opt_in` before sending anything.
* Technical dashboard for delivery health and SMS usage/cost tracking.
* Wires the trigger table from the spec into next_base/next_booking/
  next_front_desk/next_housekeeping/next_maintenance/next_pos_integration.
  next_owner_portal and next_channel_manager call back into this module's
  `next.sms.template.send_trigger()` API directly, since they install after it.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': [
        'next_base', 'next_booking', 'next_front_desk',
        'next_housekeeping', 'next_maintenance', 'next_pos_integration',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/next_sms_templates.xml',
        'data/next_sms_cron.xml',
        'views/next_sms_provider_views.xml',
        'views/next_sms_template_views.xml',
        'views/next_sms_log_views.xml',
        'views/next_sms_dashboard_views.xml',
        'views/next_sms_menus.xml',
    ],
    'installable': True,
    'application': False,
}
