# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class NextReservation(models.Model):
    _inherit = 'next.reservation'

    inventory_item_ids = fields.One2many('next.guest.inventory.item', 'reservation_id',
                                          string='Guest Inventory Items')
    checkout_reconciled = fields.Boolean(default=False, copy=False,
                                          help='Set by the mandatory inventory-reconciliation wizard. '
                                               'Checkout cannot complete until this is True.')

    def action_check_in(self):
        res = super().action_check_in()
        for rec in self:
            if not rec.inventory_item_ids:
                # Seed the standard issued-item set; property/room-type specific
                # defaults can be configured by extending this list.
                rec.inventory_item_ids = [(0, 0, {
                    'name': 'Room Key / Keycard', 'category': 'key', 'quantity_issued': len(rec.room_ids) or 1,
                }), (0, 0, {
                    'name': 'TV Remote', 'category': 'remote', 'quantity_issued': len(rec.room_ids) or 1,
                })]
        return res

    def action_open_checkout_wizard(self):
        """Entry point for the Front Desk dashboard's checkout button.
        Always opens the reconciliation wizard instead of calling
        action_check_out() directly - this is the hard block."""
        self.ensure_one()
        if self.state != 'checked_in':
            raise UserError('Only checked-in reservations can be checked out.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Checkout - Inventory Reconciliation',
            'res_model': 'next.checkout.reconciliation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_reservation_id': self.id},
        }

    def action_check_out(self):
        for rec in self:
            if not rec.checkout_reconciled:
                raise UserError(
                    'Checkout is blocked: the inventory-reconciliation wizard must be completed first. '
                    'Use "Check Out" from the Front Desk dashboard.')
        return super().action_check_out()
