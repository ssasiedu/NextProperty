# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class NextQrOrderController(http.Controller):
    """Mobile-friendly self-order page reached by scanning a room's QR code.
    No login required (token-gated), so guests can order without creating a
    portal account."""

    @http.route('/qr-order/<int:room_id>/<string:token>', type='http', auth='public', website=True, sitemap=False)
    def qr_order_page(self, room_id, token, **kw):
        Room = request.env['next.room'].sudo()
        room = Room.browse(room_id)
        if not room.exists() or room._next_qr_token() != token:
            return request.render('next_pos_integration.qr_order_invalid')

        reservation = request.env['next.reservation'].sudo().search([
            ('room_ids', 'in', room.id), ('state', '=', 'checked_in'),
        ], limit=1)
        if not reservation:
            return request.render('next_pos_integration.qr_order_no_active_stay', {'room': room})

        products = request.env['product.product'].sudo().search(
            [('sale_ok', '=', True), ('available_in_pos', '=', True)], limit=50)
        return request.render('next_pos_integration.qr_order_menu', {
            'room': room, 'reservation': reservation, 'products': products, 'token': token,
        })

    @http.route('/qr-order/<int:room_id>/<string:token>/submit', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def qr_order_submit(self, room_id, token, **post):
        Room = request.env['next.room'].sudo()
        room = Room.browse(room_id)
        if not room.exists() or room._next_qr_token() != token:
            return request.redirect('/')

        reservation = request.env['next.reservation'].sudo().search([
            ('room_ids', 'in', room.id), ('state', '=', 'checked_in'),
        ], limit=1)
        if not reservation:
            return request.redirect('/qr-order/%s/%s' % (room_id, token))

        lines = []
        for key, qty in post.items():
            if key.startswith('qty_') and qty and int(qty) > 0:
                product_id = int(key.replace('qty_', ''))
                product = request.env['product.product'].sudo().browse(product_id)
                lines.append((0, 0, {
                    'product_id': product.id, 'qty': int(qty), 'price_unit': product.lst_price,
                }))
        if lines:
            request.env['next.qr.order'].sudo().create({
                'room_id': room.id, 'reservation_id': reservation.id, 'line_ids': lines,
            })
        return request.render('next_pos_integration.qr_order_thanks')
