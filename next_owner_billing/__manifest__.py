{
    'name': 'NEXT Property Management - Owner Billing (Service Charge)',
    'version': '19.0.1.0.0',
    'category': 'Industries/Hospitality',
    'summary': 'Recurring monthly service charge billed to property owners, with payment tracking and defaulter alerts',
    'description': """
NEXT Property Management - Owner Billing
===========================================
Team review item #11: "The owners of the property are charged a monthly
recurring fee of a specified amount... like a service charge from the
property manager to the property owner."

* `next.owner.service.charge`: a recurring monthly fee configured per
  owner/property - amount, billing day of month, active/paused.
* `next.owner.bill`: the actual monthly invoice raised against a service
  charge (or issued standalone) - due date, amount, running balance.
* `next.owner.bill.payment`: a payment ledger per bill (supports partial
  payments) - self-reported by the owner from their portal (awaiting
  confirmation) or recorded/confirmed directly by Accountant/Manager.
  The owner's balance is only reduced once a payment is confirmed.
* Automatic monthly bill generation, overdue/defaulter detection, and
  recurring reminder messaging (cron-driven).
* SMS/email alerts (via next_sms) when a bill is raised, when the owner
  reports a payment, when that payment is confirmed, and to defaulters.
* Owner Portal: bills, running balance, payment history and a
  downloadable statement, plus a self-service "I've Paid" report.
* Director/Management Billing Dashboard: schedule, defaulters, and who
  has paid for a given month, across every property.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'next_owner_portal', 'next_sms', 'portal'],
    'data': [
        'security/next_owner_billing_security.xml',
        'security/ir.model.access.csv',
        'data/next_owner_billing_sequence.xml',
        'data/next_owner_billing_cron.xml',
        'report/next_owner_bill_statement.xml',
        'report/next_owner_bill_statement_templates.xml',
        'views/next_owner_service_charge_views.xml',
        'views/next_owner_bill_views.xml',
        'views/res_partner_views.xml',
        'views/next_owner_billing_menus.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
