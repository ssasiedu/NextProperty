{
    'name': 'NEXT Property Management - Base',
    'version': '19.0.1.4.0',
    'category': 'Industries/Hospitality',
    'summary': 'Core data model, security groups and record rules for NEXT Property Management',
    'description': """
NEXT Property Management - Base
================================
Foundational module for the NEXT Property Management suite. Provides:

* Multi-property support (`next.property`)
* Room types and rooms (`next.room.type`, `next.room`)
* Reservations and folios (`next.reservation`, `next.folio`)
* Property-owner extension of `res.partner`
* Security groups used by every other `next_*` module
* Record rules scoping Property Owners to their own data

All other NEXT Property Management modules depend on this one.
""",
    'author': 'NEXT Property Management',
    'website': 'https://github.com/',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'account'],
    'data': [
        'security/next_security_groups.xml',
        'security/next_base_security.xml',
        'security/ir.model.access.csv',
        'data/next_sequence_data.xml',
        'views/next_property_views.xml',
        'views/next_room_type_views.xml',
        'views/next_room_views.xml',
        'views/next_reservation_views.xml',
        'report/next_folio_templates.xml',
        'report/next_folio_reports.xml',
        'views/next_folio_views.xml',
        'views/res_partner_views.xml',
        'views/next_base_menus.xml',
    ],
    'installable': True,
    'application': True,
    'assets': {},
}
