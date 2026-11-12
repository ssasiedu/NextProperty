{
    'name': 'NEXT Property Management - Executive Dashboard',
    'version': '19.0.1.1.0',
    'category': 'Industries/Hospitality',
    'summary': "A 360-degree, whole-business view across every NEXT module, plus an automated monthly director's report",
    'description': """
NEXT Property Management - Executive Dashboard
================================================
Team review item #12: "There should be an overall dashboard and director
auto report that gives a 360 view of the entire business."

* An on-screen 360 Dashboard wizard (menu: NEXT Property Mgmt > Executive
  Dashboard) for any week/month/year the director picks, rolling up:
  occupancy, ADR, RevPAR and gross revenue (next.bi.reservation.report),
  property/room profitability (next.property._get_profitability_breakdown),
  maintenance equipment health and ticket backlog
  (maintenance.equipment._get_director_report_data), live owner-billing
  defaulters and collection for the period (next.owner.bill), live
  housekeeping task backlog, and F&B/QR self-order revenue for the period.
  Every figure is read from the one place each is already computed
  elsewhere in the suite - nothing here is recalculated from scratch.
* A matching "Director's Report" PDF, printable on demand from the same
  wizard.
* A monthly `ir.cron` that automatically generates that same PDF for the
  month just ended and emails it to every Manager-group user - the "auto
  report" the request asks for, with no one needing to remember to run it.
* The dashboard and report also break down maintenance ticket activity for
  the selected period (opened/resolved/pending/completed) and the upcoming
  preventive maintenance due, with the cost of letting it slide, both
  already incurred this period and currently at risk.
* A second dashboard (menu: NEXT Property Mgmt > Property Dashboard) gives
  a property manager the exact same view, narrowed to one property - same
  aggregator, same layout, same PDF structure, just property-scoped. A
  manager of exactly one property lands on it with nothing to pick.

Scoped to the Manager/Accountant groups - this is an internal, whole-
business (or single-property) view, never shown to a Property Owner.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': [
        'next_base', 'next_booking', 'next_maintenance', 'next_housekeeping',
        'next_owner_portal', 'next_owner_billing', 'next_pos_integration',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/next_dashboard_cron.xml',
        'report/next_business_director_report.xml',
        'report/next_business_director_report_templates.xml',
        'report/next_property_manager_report.xml',
        'report/next_property_manager_report_templates.xml',
        'wizard/next_business_dashboard_wizard_views.xml',
        'wizard/next_property_dashboard_wizard_views.xml',
        'views/next_dashboard_menus.xml',
    ],
    'installable': True,
    'application': False,
}
