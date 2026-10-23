{
    'name': 'NEXT Property Management - Owner Portal',
    'version': '19.0.1.0.0',
    'category': 'Industries/Hospitality',
    'summary': 'Owner BI dashboard, manual net revenue, expenses, settlement statements, property viewings',
    'description': """
NEXT Property Management - Owner Portal
==========================================
* Internal BI dashboard: gross revenue trend, occupancy, booking-source
  split, cancellations, ADR, RevPAR (internal only).
* `next.owner.net.revenue`: the ONLY net-revenue figure ever shown to a
  Property Owner is the manually entered, locked/audited one. System-
  computed net revenue is never exposed on the Owner Portal.
* `next.room.expense` and per-room net-income calculation (internal,
  reconciled against the manual figure before anything publishes).
* Owner Settlement/Payout Statement PDF.
* `next.property.viewing` integrated with Calendar for slot-based scheduling.
* Live, colour-coded room status exposed to owners, scoped to their rooms.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'next_sms', 'calendar', 'portal'],
    'data': [
        'security/next_owner_portal_security.xml',
        'security/ir.model.access.csv',
        'data/next_sequence_data.xml',
        'report/next_owner_settlement_report.xml',
        'report/next_owner_settlement_templates.xml',
        'views/next_owner_net_revenue_views.xml',
        'views/next_room_expense_views.xml',
        'views/next_property_viewing_views.xml',
        'views/next_owner_bi_dashboard_views.xml',
        'views/next_owner_portal_menus.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
