# -*- coding: utf-8 -*-
from odoo import api, models


class NextReservation(models.Model):
    _inherit = 'next.reservation'

    @api.model
    def pos_search_in_house(self, property_id=False, term=''):
        """Used by the POS "Bill to Room" payment flow (see
        next_pos_integration/static/src/js/room_charge_dialog.js) to let
        front-of-house staff find the guest stay to charge. Limited to
        checked-in stays - that is the only state where "the room" is
        actually occupied by someone who can be billed.

        Returns light dicts rather than full records/display_name, since
        this is called over RPC from the POS frontend for every keystroke
        of a search box."""
        domain = [('state', '=', 'checked_in')]
        if property_id:
            domain.append(('property_id', '=', property_id))
        if term:
            domain += ['|', ('partner_id.name', 'ilike', term), ('room_ids.name', 'ilike', term)]
        reservations = self.search(domain, limit=20)
        return [{
            'id': r.id,
            'guest_name': r.partner_id.name,
            'rooms': ', '.join(r.room_ids.mapped('name')) or '(no room)',
            'property_name': r.property_id.name,
        } for r in reservations]
