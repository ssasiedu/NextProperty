# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextFolio(models.Model):
    """Consolidated billing record for a stay. Aggregates room-charge lines,
    POS order lines (posted by next_pos_integration) and repair/damage charge
    lines (posted by next_front_desk's inventory-reconciliation wizard) into
    one itemized document at checkout."""
    _name = 'next.folio'
    _description = 'Folio'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(copy=False, readonly=True, default='New')
    reservation_id = fields.Many2one('next.reservation', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Guest', required=True)
    property_id = fields.Many2one('next.property', required=True)
    currency_id = fields.Many2one(related='property_id.currency_id', store=True)

    state = fields.Selection([
        ('open', 'Open'),
        ('finalized', 'Finalized'),
        ('invoiced', 'Invoiced'),
    ], default='open', required=True, copy=False, tracking=True)

    line_ids = fields.One2many('next.folio.line', 'folio_id', string='Lines')
    amount_total = fields.Monetary(compute='_compute_amount_total', store=True)

    move_id = fields.Many2one('account.move', string='Invoice', copy=False, readonly=True)

    # Guest sign-off at checkout: every charge on this folio (room, POS,
    # damage/discrepancy) is shown on the printed bill (report_next_folio)
    # for the guest to sign - either digitally here via the signature pad
    # widget, or on the printed paper copy.
    signature = fields.Binary(string='Guest Signature', copy=False, attachment=True)
    signed_name = fields.Char(string='Signed By', copy=False,
                               help='Typed/confirmed name of the guest (or whoever signs) for the record.')
    signed_date = fields.Datetime(string='Signed On', readonly=True, copy=False)

    def write(self, vals):
        if vals.get('signature') and not vals.get('signed_date'):
            vals = dict(vals, signed_date=fields.Datetime.now())
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('next.folio') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('amount'))

    def add_line(self, description, amount, line_type='other', quantity=1.0, source_ref=None):
        """Generic entry point used by next_pos_integration (POS lines),
        next_front_desk (reconciliation discrepancy charges) and room-charge
        auto-posting to append a line without duplicating folio logic."""
        self.ensure_one()
        vals = {
            'folio_id': self.id,
            'description': description,
            'line_type': line_type,
            'quantity': quantity,
            'amount': amount,
        }
        if source_ref:
            vals['source_model'] = source_ref._name
            vals['source_res_id'] = source_ref.id
        return self.env['next.folio.line'].create(vals)

    def action_finalize(self):
        """Called when the reservation checks out. Posts the room-charge
        line(s) if not already present, then locks the folio for invoicing."""
        for rec in self:
            if not rec.line_ids.filtered(lambda l: l.line_type == 'room_charge'):
                reservation = rec.reservation_id
                nightly = sum(reservation.room_ids.mapped('room_type_id.list_price'))
                if nightly and reservation.nights:
                    rec.add_line('Room charge (%s nights)' % reservation.nights,
                                 nightly * reservation.nights, line_type='room_charge')
            rec.state = 'finalized'

    def action_create_invoice(self):
        """Builds a single itemized account.move from all folio lines:
        room charges + POS lines + repair/damage charges."""
        AccountMove = self.env['account.move']
        for rec in self:
            if rec.move_id:
                continue
            invoice_lines = [(0, 0, {
                'name': line.description,
                'quantity': line.quantity,
                'price_unit': line.amount / (line.quantity or 1.0),
            }) for line in rec.line_ids]
            move = AccountMove.create({
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'invoice_line_ids': invoice_lines,
                'invoice_origin': rec.name,
            })
            rec.write({'move_id': move.id, 'state': 'invoiced'})
        return True


class NextFolioLine(models.Model):
    _name = 'next.folio.line'
    _description = 'Folio Line'
    _order = 'id'

    folio_id = fields.Many2one('next.folio', required=True, ondelete='cascade')
    description = fields.Char(required=True)
    line_type = fields.Selection([
        ('room_charge', 'Room Charge'),
        ('pos', 'POS Order'),
        ('damage', 'Repair/Damage Charge'),
        ('service', 'Service/QR Order'),
        ('other', 'Other'),
    ], default='other', required=True)
    quantity = fields.Float(default=1.0)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related='folio_id.currency_id', store=True)

    source_model = fields.Char(help='Technical name of the originating record model, if any.')
    source_res_id = fields.Integer(help='ID of the originating record, if any.')
