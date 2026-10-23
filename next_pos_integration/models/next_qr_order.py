# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextQrOrder(models.Model):
    """A guest self-order placed by scanning their room's QR code. Lightweight
    model (not a full POS order) that: (1) posts the charge to the guest's
    active folio immediately, and (2) creates a draft pos.order so kitchen/
    service staff see it on their normal POS order tickets/screen."""
    _name = 'next.qr.order'
    _description = 'QR Self-Order'
    _order = 'create_date desc'

    room_id = fields.Many2one('next.room', required=True)
    reservation_id = fields.Many2one('next.reservation', required=True)
    line_ids = fields.One2many('next.qr.order.line', 'qr_order_id', string='Items')
    amount_total = fields.Monetary(compute='_compute_amount_total', store=True)
    currency_id = fields.Many2one(related='reservation_id.currency_id', store=True)

    status = fields.Selection([
        ('new', 'Received'),
        ('confirmed', 'Confirmed'),
        ('ready', 'Ready / Service Complete'),
    ], default='new', required=True)

    pos_order_id = fields.Many2one('pos.order', readonly=True, copy=False)
    folio_line_id = fields.Many2one('next.folio.line', readonly=True, copy=False)

    @api.depends('line_ids.subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('subtotal'))

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            order._post_to_folio_and_notify_staff()
            # next_sms: 'Order received/confirmed' trigger fires to the guest here.
        return orders

    def _post_to_folio_and_notify_staff(self):
        for order in self:
            folio = order.reservation_id.folio_id
            line = folio.add_line(
                description='QR Order (%s)' % order.room_id.name,
                amount=order.amount_total, line_type='service', source_ref=order)
            order.folio_line_id = line.id
            order.status = 'confirmed'
            # Create a draft POS order so the item shows on the normal
            # kitchen/service POS order-ticket screen, without taking a
            # separate payment (it is already on the folio).
            pos_config = self.env['pos.config'].search(
                [('next_property_id', '=', order.room_id.property_id.id)], limit=1)
            if pos_config:
                order.pos_order_id = self.env['pos.order'].create({
                    'company_id': pos_config.company_id.id,
                    'session_id': pos_config.current_session_id.id if pos_config.current_session_id else False,
                    'next_reservation_id': order.reservation_id.id,
                    'lines': [(0, 0, {
                        'product_id': line.product_id.id,
                        'qty': line.qty,
                        'price_unit': line.price_unit,
                        'price_subtotal': line.subtotal,
                        'price_subtotal_incl': line.subtotal,
                    }) for line in order.line_ids],
                }).id if pos_config.current_session_id else False

    def action_mark_ready(self):
        self.write({'status': 'ready'})
        # next_sms: 'Order ready/service complete' trigger fires to the guest here.


class NextQrOrderLine(models.Model):
    _name = 'next.qr.order.line'
    _description = 'QR Self-Order Line'

    qr_order_id = fields.Many2one('next.qr.order', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    qty = fields.Float(default=1.0)
    price_unit = fields.Float()
    subtotal = fields.Float(compute='_compute_subtotal', store=True)

    @api.depends('qty', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.qty * rec.price_unit
