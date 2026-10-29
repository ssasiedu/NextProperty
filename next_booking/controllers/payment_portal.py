# -*- coding: utf-8 -*-
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal


class NextBookingPaymentPortal(PaymentPortal):
    """The generic /payment/confirmation page (payment.confirm) is shared by
    every payment flow in the database, and its one call to action is
    hardcoded to href="/my/home" - auth='user', so a public/anonymous guest
    (every website booking, unless they happened to be logged in) who had
    just paid got bounced to a login wall right after finishing payment,
    with no indication the booking was actually received.

    Rather than touch that shared template (other payment flows may
    legitimately want "Go to my Account"), this overrides the route to
    render a NEXT-specific confirmation page - reusing the same
    payment.state_header/payment.summary_item building blocks for a
    consistent look - whenever the transaction is one of ours
    (payment_transaction.py's _find_next_reservation), and falls back to
    the stock page for every other transaction."""

    @http.route('/payment/confirmation', type='http', methods=['GET'], auth='public', website=True)
    def payment_confirm(self, tx_id, access_token, **kwargs):
        tx_id_int = self._cast_as_int(tx_id)
        if tx_id_int:
            tx_sudo = request.env['payment.transaction'].sudo().browse(tx_id_int)
            if not payment_utils.check_access_token(
                    access_token, tx_sudo.partner_id.id, tx_sudo.amount, tx_sudo.currency_id.id):
                raise NotFound()  # Don't leak information about ids.
            reservation = tx_sudo._find_next_reservation()
            if reservation:
                return request.render('next_booking.booking_payment_confirm', {
                    'tx': tx_sudo, 'reservation': reservation,
                })
        return super().payment_confirm(tx_id, access_token, **kwargs)
