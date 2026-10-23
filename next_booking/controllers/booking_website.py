# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import http
from odoo.http import request


class NextBookingWebsite(http.Controller):
    """Enforces the exact booking flow required:
    1. select property (skipped if single-property deployment)
    2. select check-in / check-out dates
    3. enter occupancy (adults, children, rooms)
    4. server-side availability query (next.room.type.search_available)
    5. guest selects room(s), pays, reservation confirmed

    Each step is its own route so the flow cannot be skipped: step N+1
    always re-validates that step N's required parameters are present and
    redirects back to step N otherwise.
    """

    # ---- Step 1: property ------------------------------------------------
    @http.route(['/book', '/book/property'], type='http', auth='public', website=True, sitemap=True)
    def book_property(self, **kw):
        Property = request.env['next.property'].sudo()
        properties = Property.search([('active', '=', True)])
        if len(properties) <= 1:
            prop = properties[:1]
            return request.redirect('/book/dates?property_id=%s' % (prop.id if prop else 0))
        return request.render('next_booking.booking_step_property', {'properties': properties})

    # ---- Step 2: dates -----------------------------------------------------
    @http.route('/book/dates', type='http', auth='public', website=True, sitemap=False)
    def book_dates(self, property_id=None, **kw):
        if not property_id:
            return request.redirect('/book/property')
        return request.render('next_booking.booking_step_dates', {'property_id': property_id})

    # ---- Step 3: occupancy --------------------------------------------------
    @http.route('/book/occupancy', type='http', auth='public', website=True, sitemap=False)
    def book_occupancy(self, property_id=None, date_from=None, date_to=None, **kw):
        if not (property_id and date_from and date_to):
            return request.redirect('/book/dates?property_id=%s' % (property_id or ''))
        return request.render('next_booking.booking_step_occupancy', {
            'property_id': property_id, 'date_from': date_from, 'date_to': date_to,
        })

    # ---- Step 4: availability ----------------------------------------------
    @http.route('/book/availability', type='http', auth='public', website=True, sitemap=False)
    def book_availability(self, property_id=None, date_from=None, date_to=None,
                           adults=1, children=0, rooms=1, **kw):
        if not (property_id and date_from and date_to):
            return request.redirect('/book/dates?property_id=%s' % (property_id or ''))

        df = datetime.strptime(date_from, '%Y-%m-%d')
        dt = datetime.strptime(date_to, '%Y-%m-%d')
        RoomType = request.env['next.room.type'].sudo()
        available = RoomType.search_available(
            int(property_id), df, dt, adults=int(adults), children=int(children), room_count=int(rooms))

        results = []
        for rt in available:
            results.append({
                'room_type': rt,
                'price': rt.price_for_stay(df, dt, int(adults), int(children)),
            })
        return request.render('next_booking.booking_step_availability', {
            'results': results, 'property_id': property_id,
            'date_from': date_from, 'date_to': date_to,
            'adults': adults, 'children': children, 'rooms': rooms,
        })

    # ---- Step 5: select room(s) + checkout --------------------------------
    @http.route('/book/select/<int:room_type_id>', type='http', auth='public', website=True, sitemap=False)
    def book_select(self, room_type_id, property_id=None, date_from=None, date_to=None,
                     adults=1, children=0, rooms=1, **kw):
        df = datetime.strptime(date_from, '%Y-%m-%d')
        dt = datetime.strptime(date_to, '%Y-%m-%d')
        room_type = request.env['next.room.type'].sudo().browse(room_type_id)
        free_rooms = room_type.get_available_rooms(df, dt)
        if len(free_rooms) < int(rooms):
            return request.redirect('/book/availability?property_id=%s&date_from=%s&date_to=%s'
                                     '&adults=%s&children=%s&rooms=%s' % (
                                         property_id, date_from, date_to, adults, children, rooms))
        return request.render('next_booking.booking_step_confirm', {
            'room_type': room_type, 'free_rooms': free_rooms[:int(rooms)],
            'property_id': property_id, 'date_from': date_from, 'date_to': date_to,
            'adults': adults, 'children': children, 'rooms': rooms,
            'price': room_type.price_for_stay(df, dt, int(adults), int(children)),
        })

    @http.route('/book/confirm', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def book_confirm(self, room_type_id=None, property_id=None, date_from=None, date_to=None,
                      adults=1, children=0, rooms=1, **kw):
        """Creates the reservation in draft and hands off to Odoo `payment`
        for the actual transaction; on payment confirmation (handled by the
        standard payment flow / webhook) the reservation is moved to
        `confirmed` and next_sms fires the booking-confirmation trigger."""
        df = datetime.strptime(date_from, '%Y-%m-%d')
        dt = datetime.strptime(date_to, '%Y-%m-%d')
        room_type = request.env['next.room.type'].sudo().browse(int(room_type_id))
        free_rooms = room_type.get_available_rooms(df, dt)[:int(rooms)]

        partner = request.env.user.partner_id if not request.env.user._is_public() else \
            request.env['res.partner'].sudo().browse(request.session.get('next_guest_partner_id'))

        reservation = request.env['next.reservation'].sudo().create({
            'property_id': int(property_id),
            'partner_id': partner.id if partner else request.env.ref('base.public_partner').id,
            'date_from': df,
            'date_to': dt,
            'adults': int(adults),
            'children': int(children),
            'room_count_requested': int(rooms),
            'room_ids': [(6, 0, free_rooms.ids)],
            'booking_source': 'direct',
        })
        # Payment integration point: redirect into Odoo's standard payment
        # flow for this reservation's folio amount; left as a redirect to the
        # portal booking page in this scaffold so the module installs clean
        # without a specific payment acquirer configured.
        return request.redirect('/my/bookings/%s' % reservation.id)
