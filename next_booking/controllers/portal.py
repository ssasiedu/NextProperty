# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class NextGuestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'reservation_count' in counters:
            values['reservation_count'] = request.env['next.reservation'].search_count(
                [('partner_id', '=', partner.id)])
        if 'service_request_count' in counters:
            values['service_request_count'] = request.env['next.service.request'].search_count(
                [('partner_id', '=', partner.id)])
        return values

    # ---- Booking history / upcoming reservations --------------------------
    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_bookings(self, page=1, **kw):
        partner = request.env.user.partner_id
        Reservation = request.env['next.reservation']
        domain = [('partner_id', '=', partner.id)]
        pager = portal_pager(url='/my/bookings', total=Reservation.search_count(domain), page=page, step=20)
        reservations = Reservation.search(domain, limit=20, offset=pager['offset'], order='date_from desc')
        return request.render('next_booking.portal_my_bookings', {
            'reservations': reservations, 'pager': pager, 'page_name': 'bookings',
        })

    @http.route('/my/bookings/<int:reservation_id>', type='http', auth='user', website=True)
    def portal_booking_detail(self, reservation_id, **kw):
        reservation = request.env['next.reservation'].browse(reservation_id)
        if reservation.partner_id != request.env.user.partner_id:
            return request.redirect('/my/bookings')
        return request.render('next_booking.portal_booking_detail', {'reservation': reservation})

    # ---- Folio / invoice history --------------------------------------------
    @http.route('/my/bookings/<int:reservation_id>/folio', type='http', auth='user', website=True)
    def portal_booking_folio(self, reservation_id, **kw):
        reservation = request.env['next.reservation'].browse(reservation_id)
        if reservation.partner_id != request.env.user.partner_id:
            return request.redirect('/my/bookings')
        return request.render('next_booking.portal_booking_folio', {'folio': reservation.folio_id})

    @http.route('/my/bookings/<int:reservation_id>/folio/pdf', type='http', auth='user', website=True)
    def portal_booking_folio_pdf(self, reservation_id, **kw):
        reservation = request.env['next.reservation'].browse(reservation_id)
        if reservation.partner_id != request.env.user.partner_id or not reservation.folio_id.move_id:
            return request.redirect('/my/bookings')
        pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'account.account_invoices', [reservation.folio_id.move_id.id])
        return request.make_response(pdf, headers=[('Content-Type', 'application/pdf')])

    # ---- Service requests ---------------------------------------------------
    @http.route(['/my/service-requests', '/my/service-requests/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_service_requests(self, page=1, **kw):
        partner = request.env.user.partner_id
        Request = request.env['next.service.request']
        domain = [('partner_id', '=', partner.id)]
        pager = portal_pager(url='/my/service-requests', total=Request.search_count(domain), page=page, step=20)
        requests_ = Request.search(domain, limit=20, offset=pager['offset'], order='create_date desc')
        return request.render('next_booking.portal_my_service_requests', {
            'service_requests': requests_, 'pager': pager, 'page_name': 'service_requests',
        })

    @http.route('/my/service-requests/new', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_new_service_request(self, **kw):
        partner = request.env.user.partner_id
        if request.httprequest.method == 'POST':
            reservation_id = int(kw.get('reservation_id'))
            reservation = request.env['next.reservation'].browse(reservation_id)
            if reservation.partner_id == partner:
                request.env['next.service.request'].sudo().create({
                    'name': kw.get('name'),
                    'reservation_id': reservation_id,
                    'request_type': kw.get('request_type', 'general'),
                    'description': kw.get('description'),
                })
            return request.redirect('/my/service-requests')
        reservations = request.env['next.reservation'].search([
            ('partner_id', '=', partner.id), ('state', 'in', ('confirmed', 'checked_in'))])
        return request.render('next_booking.portal_new_service_request', {'reservations': reservations})
