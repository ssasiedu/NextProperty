# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    """Bridges POS orders to next.folio. When a POS order is tagged with an
    active `next.reservation` (via the POS payment screen's "Bill to Room"
    flow - see next_pos_integration/static/src/js - or the QR self-order
    controller), it posts as a folio line instead of becoming a standalone
    POS invoice - the final itemized document is the folio, produced at
    checkout in next_base.next_folio.action_create_invoice.

    Note: Odoo 19 removed the old `_order_fields`/`create_from_ui` API this
    used to rely on. Orders are now synced via `sync_from_ui` ->
    `_process_order`, which passes the whole frontend order dict straight to
    create()/write() with no field whitelist - so `next_reservation_id`
    reaches this model automatically as long as the frontend sends it
    (handled by the PosOrder JS model patch's serializeForORM override)."""
    _inherit = 'pos.order'

    next_reservation_id = fields.Many2one('next.reservation', string='Guest Stay',
                                           help='When set, this order is charged to the '
                                                'guest\'s folio instead of invoiced standalone.')
    next_folio_line_id = fields.Many2one('next.folio.line', readonly=True, copy=False)

    def _next_post_to_folio(self):
        for order in self:
            if not order.next_reservation_id or order.next_folio_line_id:
                continue
            folio = order.next_reservation_id.folio_id
            line = folio.add_line(
                description='POS Order %s' % order.pos_reference,
                amount=order.amount_total,
                line_type='pos',
                source_ref=order,
            )
            order.next_folio_line_id = line.id
            # Mark the POS order itself as settled against the folio rather
            # than invoiced/paid through a standalone POS payment method.
            order.message_post(body='Posted to folio %s (guest stay %s).' % (
                folio.name, order.next_reservation_id.name))

    def action_pos_order_paid(self):
        # Defense in depth: if a "Room Charge" payment line somehow reached
        # here without a guest stay attached (a JS bug, or the field getting
        # dropped some other way), fail loudly here rather than silently
        # losing the charge - better a blocked checkout than an unbilled stay.
        for order in self:
            has_room_charge_line = any(p.payment_method_id.next_is_room_charge for p in order.payment_ids)
            if has_room_charge_line and not order.next_reservation_id:
                raise UserError(
                    'This order has a "Room Charge" payment line but no guest stay was selected. '
                    'Please contact a manager before completing this sale.')
        res = super().action_pos_order_paid()
        self.filtered('next_reservation_id')._next_post_to_folio()
        return res


class PosConfig(models.Model):
    _inherit = 'pos.config'

    next_property_id = fields.Many2one('next.property', string='NEXT Property',
                                        help='Links this POS point of sale to a property so staff can '
                                             'quickly pick an active in-house guest stay to charge.')
