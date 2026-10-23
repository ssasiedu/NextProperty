# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextGuestInventoryItem(models.Model):
    """An item issued to a guest for the duration of a stay (room key,
    TV remote, minibar stock, towels, equipment...). Created when the guest
    checks in (or added manually by front desk), and reconciled by the
    mandatory checkout wizard before the reservation can move to
    `checked_out`."""
    _name = 'next.guest.inventory.item'
    _description = 'Guest Inventory Item'
    _order = 'id'

    reservation_id = fields.Many2one('next.reservation', required=True, ondelete='cascade')
    name = fields.Char(string='Item', required=True)
    category = fields.Selection([
        ('key', 'Key / Keycard'),
        ('remote', 'Remote Control'),
        ('minibar', 'Minibar'),
        ('towels', 'Towels/Linen'),
        ('equipment', 'Equipment'),
        ('other', 'Other'),
    ], default='other', required=True)
    quantity_issued = fields.Float(default=1.0)
    quantity_returned = fields.Float(default=0.0)
    unit_value = fields.Monetary(string='Replacement Value', currency_field='currency_id')
    currency_id = fields.Many2one(related='reservation_id.currency_id', store=True)

    reconciled = fields.Boolean(default=False, copy=False)
    discrepancy_qty = fields.Float(compute='_compute_discrepancy', store=True)
    discrepancy_charge = fields.Monetary(compute='_compute_discrepancy', store=True, currency_field='currency_id')

    @api.depends('quantity_issued', 'quantity_returned', 'unit_value')
    def _compute_discrepancy(self):
        for rec in self:
            missing = max(rec.quantity_issued - rec.quantity_returned, 0.0)
            rec.discrepancy_qty = missing
            rec.discrepancy_charge = missing * rec.unit_value
