# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    """A payment method flagged `next_is_room_charge` represents "bill this
    to the guest's room" rather than an actual tender (cash/card/terminal).
    Selecting it on the POS Payment screen opens a guest-stay picker (see
    static/src/js/payment_screen_patch.js) instead of collecting payment;
    the order is then posted to that guest's folio by PosOrder._next_post_to_folio
    instead of being paid for at the till.

    Create one such method (e.g. named "Room Charge", no journal needed) and
    add it to the relevant POS config's payment methods."""
    _inherit = 'pos.payment.method'

    next_is_room_charge = fields.Boolean(
        string='Bill to Guest Room',
        help='When enabled, selecting this payment method on the Payment screen opens a guest-stay '
             "picker instead of taking cash/card: the order is posted to that guest's folio instead "
             'of being paid for at the till.')

    @api.model
    def _load_pos_data_fields(self, config):
        # pos.payment.method restricts the fields sent to the POS frontend to
        # an explicit list (unlike e.g. pos.order, which sends everything by
        # default) - a new field has to be added to that list explicitly or
        # the frontend will never see it. Same pattern core's own
        # pos_restaurant module uses for pos.preset.use_guest.
        return super()._load_pos_data_fields(config) + ['next_is_room_charge']
