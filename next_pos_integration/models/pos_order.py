# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosOrder(models.Model):
    """Bridges POS orders to next.folio. When a POS order is tagged with an
    active `next.reservation` (via the POS session's room-charge flow, or
    the QR self-order controller), it posts as a folio line instead of
    becoming a standalone POS invoice - the final itemized document is the
    folio, produced at checkout in next_base.next_folio.action_create_invoice."""
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
        res = super().action_pos_order_paid()
        self.filtered('next_reservation_id')._next_post_to_folio()
        return res

    @api.model
    def _order_fields(self, ui_order):
        fields_ = super()._order_fields(ui_order)
        if ui_order.get('next_reservation_id'):
            fields_['next_reservation_id'] = ui_order['next_reservation_id']
        return fields_


class PosConfig(models.Model):
    _inherit = 'pos.config'

    next_property_id = fields.Many2one('next.property', string='NEXT Property',
                                        help='Links this POS point of sale to a property so staff can '
                                             'quickly pick an active in-house guest stay to charge.')
