{
    'name': 'NEXT Property Management - POS Integration & QR Ordering',
    'version': '19.0.1.0.0',
    'category': 'Industries/Hospitality',
    'summary': 'Bridges POS orders into guest folios and provides per-room QR self-ordering',
    'description': """
NEXT Property Management - POS Integration
=============================================
* Any POS order tagged to an active reservation posts as a folio line instead
  of a standalone POS invoice, so final checkout is one itemized document:
  room charges + POS lines + repair/damage charges.
* "Bill to Room": a dedicated payment method (flagged `next_is_room_charge`)
  that, instead of taking cash/card on the Payment screen, opens a guest-stay
  picker (by room number or guest name) and charges the order straight to
  that guest's folio. See static/src/js/payment_screen_patch.js.
* Generates a unique QR code per `next.room` linking to a mobile-friendly
  self-order page, posting orders directly to the guest's folio and
  notifying kitchen/service staff via POS order tickets.
""",
    'author': 'NEXT Property Management',
    'license': 'LGPL-3',
    'depends': ['next_base', 'point_of_sale'],
    'external_dependencies': {'python': ['qrcode']},
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_views.xml',
        'views/pos_payment_method_views.xml',
        'views/qr_order_templates.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'next_pos_integration/static/src/**/*',
        ],
    },
    'installable': True,
    'application': False,
}
