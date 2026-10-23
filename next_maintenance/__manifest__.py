{
    'name': 'NEXT Property Management - Maintenance',
    'version': '19.0.1.0.0',
    'category': 'Industries/Hospitality',
    'summary': 'Repair/fault request management extending Odoo Maintenance',
    'description': """
NEXT Property Management - Maintenance
=========================================
* `next.maintenance.request` inherits `maintenance.request`, raisable by
  guest (portal), housekeeping, or front desk against a specific room/asset.
* State machine: new -> assigned -> in_progress -> resolved -> verified.
* While open, can auto-block the room (grey_blocked), excluding it from
  booking availability until resolved.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'next_booking', 'maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'views/next_maintenance_request_views.xml',
        'views/next_maintenance_menus.xml',
    ],
    'installable': True,
    'application': False,
}
