# -*- coding: utf-8 -*-
from datetime import datetime
from urllib.parse import urlencode

from odoo import http
from odoo.http import request
from odoo.addons.payment import utils as payment_utils


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
        return request.render('next_booking.booking_step_confirm', self._confirm_page_values(
            room_type, free_rooms[:int(rooms)], property_id, date_from, date_to,
            adults, children, rooms, df, dt))

    def _confirm_page_values(self, room_type, free_rooms, property_id, date_from, date_to,
                              adults, children, rooms, df, dt, error=None,
                              guest_name='', guest_email='', guest_phone=''):
        """Shared by the initial GET (book_select) and the POST error
        re-render in book_confirm below, so both always pass the same set
        of keys the template expects - is_public decides whether the
        guest-details fields show at all (a logged-in portal/internal user
        already has a real partner_id, nothing to collect)."""
        return {
            'room_type': room_type, 'free_rooms': free_rooms,
            'property_id': property_id, 'date_from': date_from, 'date_to': date_to,
            'adults': adults, 'children': children, 'rooms': rooms,
            'price': room_type.price_for_stay(df, dt, int(adults), int(children)),
            'is_public': request.env.user._is_public(),
            'error': error, 'guest_name': guest_name, 'guest_email': guest_email, 'guest_phone': guest_phone,
        }

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

        # A public/anonymous booker has no partner_id of their own - without
        # this, partner_id silently fell back to the shared base.public_partner
        # placeholder and front desk had no actual guest name, email or phone
        # to follow up on for ANY online booking. Logged-in users (portal or
        # internal) already have a real partner_id, so nothing to collect.
        if request.env.user._is_public():
            guest_name = (kw.get('guest_name') or '').strip()
            guest_email = (kw.get('guest_email') or '').strip()
            guest_phone = (kw.get('guest_phone') or '').strip()
            if not guest_name or not guest_email:
                return request.render('next_booking.booking_step_confirm', self._confirm_page_values(
                    room_type, free_rooms, property_id, date_from, date_to, adults, children, rooms, df, dt,
                    error='Please enter your name and email so the front desk can confirm your booking.',
                    guest_name=guest_name, guest_email=guest_email, guest_phone=guest_phone))
            partner = request.env['res.partner'].sudo()._find_or_create_guest(
                guest_name, guest_email, guest_phone)
            # Makes this session's next booking (and any other code reading
            # this key) resolve to the same contact instead of creating a
            # second one, without requiring the guest to log in.
            request.session['next_guest_partner_id'] = partner.id
        else:
            partner = request.env.user.partner_id

        reservation = request.env['next.reservation'].sudo().create({
            'property_id': int(property_id),
            'partner_id': partner.id,
            'date_from': df,
            'date_to': dt,
            'adults': int(adults),
            'children': int(children),
            'room_count_requested': int(rooms),
            'room_ids': [(6, 0, free_rooms.ids)],
            'booking_source': 'direct',
        })
        # The confirm page just showed the guest a non-zero total
        # (price_for_stay, recomputed here rather than trusted from the
        # client) but next.reservation.create() leaves the folio with no
        # lines at all - action_finalize() only ever posts the room-charge
        # line at checkout, which is fine for front-desk/OTA flows nobody
        # looks at before then, but left every online booking's folio
        # showing 0 against a price the guest already saw. Posting it now,
        # at the same amount, means action_finalize()'s own
        # already-has-a-room_charge-line guard simply skips re-posting it
        # at checkout - no double charge.
        price = room_type.price_for_stay(df, dt, int(adults), int(children))
        if price and reservation.folio_id:
            reservation.folio_id.add_line(
                'Room charge (%s nights)' % reservation.nights, price, line_type='room_charge')

        # Hand off into Odoo's own generic payment flow (already a next_booking
        # dependency) rather than /my/bookings - that route is auth='user', so
        # a public/anonymous guest (every website booking, unless they happened
        # to be logged in) was bounced straight to a login wall immediately
        # after booking, with the reservation left unpaid and unconfirmed.
        # /payment/pay is auth='public' and handles exactly this "pay for an
        # arbitrary record, no account required" case; payment_transaction.py
        # (_post_process override) confirms the reservation and records the
        # payment once the transaction actually completes.
        amount_due = reservation.folio_id.amount_due if reservation.folio_id else 0.0
        if amount_due > 0:
            access_token = payment_utils.generate_access_token(
                partner.id, amount_due, reservation.currency_id.id)
            pay_params = {
                'reference': reservation.name,
                'amount': amount_due,
                'currency_id': reservation.currency_id.id,
                'partner_id': partner.id,
                'access_token': access_token,
            }
            return request.redirect('/payment/pay?%s' % urlencode(pay_params))

        # Nothing to pay (e.g. a 0-price stay) - nothing for /payment/pay to
        # do either, so there's no payment event left to confirm it the way
        # payment_transaction.py does for a paid booking. Confirm it here
        # instead of leaving it stuck in 'draft' forever.
        reservation.action_confirm()
        if not request.env.user._is_public():
            return request.redirect('/my/bookings/%s' % reservation.id)
        return request.render('next_booking.booking_step_thankyou', {'reservation': reservation})
