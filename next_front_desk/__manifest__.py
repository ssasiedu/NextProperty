{
    'name': 'NEXT Property Management - Front Desk',
    'version': '19.0.1.0.0',
    'category': 'Industries/Hospitality',
    'summary': 'Room status dashboard, check-in/out, guest inventory & checkout reconciliation',
    'description': """
NEXT Property Management - Front Desk
=======================================
* Kanban/Gantt hybrid dashboard of every room coloured by status.
* One-click check-in / check-out, drag-and-drop room reassignment.
* Guest inventory items issued per stay (keys, remote, minibar, towels...).
* Mandatory inventory-reconciliation wizard: checkout is hard-blocked until
  staff confirm all issued items are returned. Discrepancies post an extra
  charge line to the folio automatically.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base'],
    'data': [
        'security/ir.model.access.csv',
        'views/next_guest_inventory_item_views.xml',
        'wizard/next_checkout_reconciliation_views.xml',
        'views/next_front_desk_dashboard_views.xml',
        'views/next_front_desk_menus.xml',
    ],
    'installable': True,
    'application': False,
}
