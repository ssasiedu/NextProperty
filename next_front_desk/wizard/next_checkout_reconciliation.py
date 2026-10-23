# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class NextCheckoutReconciliationWizard(models.TransientModel):
    """Mandatory step between 'checked_in' and 'checked_out'. Staff must
    confirm the quantity returned for every issued guest-inventory item.
    Any shortfall automatically becomes a discrepancy charge line on the
    folio, and the room is then allowed to transition to checked_out."""
    _name = 'next.checkout.reconciliation.wizard'
    _description = 'Checkout Inventory Reconciliation'

    reservation_id = fields.Many2one('next.reservation', required=True)
    line_ids = fields.One2many('next.checkout.reconciliation.wizard.line', 'wizard_id', string='Items')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        reservation_id = self.env.context.get('default_reservation_id')
        if reservation_id:
            reservation = self.env['next.reservation'].browse(reservation_id)
            res['line_ids'] = [(0, 0, {
                'inventory_item_id': item.id,
                'name': item.name,
                'quantity_issued': item.quantity_issued,
                'quantity_returned': item.quantity_issued,  # default assumption: all returned
            }) for item in reservation.inventory_item_ids]
        return res

    def action_confirm(self):
        self.ensure_one()
        reservation = self.reservation_id
        total_discrepancy = 0.0
        for line in self.line_ids:
            item = line.inventory_item_id
            item.write({'quantity_returned': line.quantity_returned, 'reconciled': True})
            if item.discrepancy_charge:
                total_discrepancy += item.discrepancy_charge

        if total_discrepancy:
            reservation.folio_id.add_line(
                'Inventory discrepancy (items not returned)', total_discrepancy,
                line_type='damage', source_ref=reservation)
            # next_sms wires a trigger on this: Front Desk Supervisor is notified
            # of inventory discrepancies at checkout (see next_sms README).

        reservation.write({'checkout_reconciled': True})
        reservation.action_check_out()
        return {'type': 'ir.actions.act_window_close'}


class NextCheckoutReconciliationWizardLine(models.TransientModel):
    _name = 'next.checkout.reconciliation.wizard.line'
    _description = 'Checkout Reconciliation Line'

    wizard_id = fields.Many2one('next.checkout.reconciliation.wizard', required=True, ondelete='cascade')
    inventory_item_id = fields.Many2one('next.guest.inventory.item', required=True)
    name = fields.Char(string='Item', readonly=True)
    quantity_issued = fields.Float(readonly=True)
    quantity_returned = fields.Float(required=True)
