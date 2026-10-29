{
    'name': 'NEXT Property Management - Booking Website & Guest Portal',
    'version': '19.0.1.1.0',
    'category': 'Industries/Hospitality',
    'summary': 'Website booking flow, availability engine and guest portal',
    'description': """
NEXT Property Management - Booking
===================================
* Responsive booking website (extends `website_sale` patterns / `website`)
  enforcing: property -> dates -> occupancy -> availability -> room
  selection -> payment -> confirmation.
* Server-side availability search excluding conflicting reservations,
  maintenance blocks and channel-manager holds.
* Guest Portal (extends `portal`): booking history, folio/invoice history,
  and a service-request form with a guest-visible status.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'website', 'portal', 'payment', 'maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'security/next_booking_security.xml',
        'views/next_service_request_views.xml',
        'views/next_booking_menus.xml',
        'views/website_booking_templates.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
