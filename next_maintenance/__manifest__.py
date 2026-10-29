{
    'name': 'NEXT Property Management - Maintenance',
    'version': '19.0.2.0.1',
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
* Equipment registry (extends `maintenance.equipment`) with per-property/
  room scoping, a preventive-maintenance due-date schedule, automatic
  ticket creation + overdue cost penalties, and a management dashboard
  plus periodic email report. See `next_maintenance_equipment.py`.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'next_booking', 'maintenance', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/next_maintenance_cron.xml',
        'views/next_maintenance_request_views.xml',
        'views/next_maintenance_equipment_views.xml',
        'views/next_maintenance_menus.xml',
        'views/worker_portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
