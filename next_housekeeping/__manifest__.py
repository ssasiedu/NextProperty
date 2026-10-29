{
    'name': 'NEXT Property Management - Housekeeping',
    'version': '19.0.1.1.0',
    'category': 'Industries/Hospitality',
    'summary': 'Housekeeping task management and room-status automation',
    'description': """
NEXT Property Management - Housekeeping
=========================================
* `next.housekeeping.task` with states not_started -> in_progress -> inspected -> complete.
* Auto-creates tasks on checkout events, and via a scheduled daily cron for
  routine servicing of occupied/long-stay rooms.
* Supervisor Kanban dashboard to assign/reassign and monitor progress.
* On completion, flips the room from red_pending_checkout to green_ready.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'data/next_housekeeping_cron.xml',
        'views/next_housekeeping_task_views.xml',
        'views/next_housekeeping_menus.xml',
        'views/worker_portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
