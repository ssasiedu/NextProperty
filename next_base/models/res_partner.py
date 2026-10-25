# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_property_owner = fields.Boolean(string='Is Property Owner', default=False)

    owned_property_ids = fields.Many2many(
        'next.property', 'next_property_owner_rel', 'partner_id', 'property_id',
        string='Owned Properties')
    owned_room_ids = fields.One2many('next.room', 'owner_id', string='Owned Rooms')

    sms_opt_in = fields.Boolean(
        string='SMS Opt-in', default=True,
        help='If disabled, next_sms will never send this contact a message, '
             'regardless of template triggers.')

    email_opt_in = fields.Boolean(
        string='Email Opt-in', default=True,
        help='If disabled, next_sms will never email this contact, '
             'regardless of template triggers.')

    @api.model
    def _next_owner_scoped_property_ids(self):
        """Helper used by record rules / portal controllers: the set of
        property ids the current user may see as a Property Owner."""
        partner = self.env.user.partner_id
        if not partner.is_property_owner:
            return []
        return partner.owned_property_ids.ids
