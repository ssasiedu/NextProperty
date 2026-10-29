# -*- coding: utf-8 -*-
from odoo import models


class PaymentTransaction(models.Model):
    """Closes the loop book_confirm() (booking_website.py) hands off to:
    that controller sends the guest straight into Odoo's generic
    /payment/pay flow with reference=reservation.name as the reference
    prefix. Without this override, a successfully *paid* booking would sit
    in 'draft' forever - nothing in the generic payment module knows a
    next.reservation exists, let alone that it should be confirmed once the
    transaction is done. _post_process() is the standard extension point
    other Odoo apps (sale, invoicing) use for exactly this "a payment just
    completed - go do something with the document it was for" step."""
    _inherit = 'payment.transaction'

    def _post_process(self):
        super()._post_process()
        for tx in self:
            if tx.state != 'done':
                continue
            reservation = tx._find_next_reservation()
            if not reservation or reservation.state != 'draft':
                continue  # Not one of ours, already confirmed, or cancelled - nothing to do.
            if reservation.deposit_required and not reservation.deposit_paid:
                reservation.action_record_deposit_payment(reference=tx.reference)
            elif reservation.folio_id:
                reservation.folio_id.record_payment(
                    'Online payment (%s)' % tx.reference, tx.amount,
                    payment_type='other', reference=tx.reference)
            reservation.action_confirm()

    def _find_next_reservation(self):
        """`_compute_reference` only guarantees the reference STARTS WITH the
        prefix we passed (reservation.name) - exact match first (the normal
        case - reservation names are already unique), falling back to
        stripping `_compute_reference`'s own disambiguating "-N" suffix for
        the rare collision case."""
        self.ensure_one()
        Reservation = self.env['next.reservation'].sudo()
        reservation = Reservation.search([('name', '=', self.reference)], limit=1)
        if not reservation and '-' in self.reference:
            reservation = Reservation.search([('name', '=', self.reference.rsplit('-', 1)[0])], limit=1)
        return reservation
