# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class NextReservation(models.Model):
    _name = 'next.reservation'
    _description = 'Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(required=True, copy=False, readonly=True, default='New')

    property_id = fields.Many2one('next.property', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Guest', required=True, tracking=True)

    date_from = fields.Datetime(string='Check-in', required=True, tracking=True)
    date_to = fields.Datetime(string='Check-out', required=True, tracking=True)
    nights = fields.Integer(compute='_compute_nights', store=True)

    adults = fields.Integer(default=1, required=True)
    children = fields.Integer(default=0)
    room_count_requested = fields.Integer(string='Rooms Requested', default=1)

    room_ids = fields.Many2many('next.room', 'next_reservation_room_rel', 'reservation_id', 'room_id',
                                 string='Rooms', tracking=True)

    booking_source = fields.Selection([
        ('direct', 'Direct / Website'),
        ('walk_in', 'Walk-in'),
        ('ota', 'OTA (Channel Manager)'),
    ], default='direct', required=True, tracking=True)
    ota_channel = fields.Char(string='OTA Channel', help='e.g. Airbnb, Booking.com, Expedia')
    ota_reference = fields.Char(string='OTA Reference')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)

    folio_id = fields.Many2one('next.folio', string='Folio', copy=False, readonly=True)

    actual_checkin = fields.Datetime(readonly=True, copy=False)
    actual_checkout = fields.Datetime(readonly=True, copy=False)

    company_id = fields.Many2one(related='property_id.company_id', store=True)
    currency_id = fields.Many2one(related='property_id.currency_id', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('next.reservation') or 'New'
        records = super().create(vals_list)
        for rec in records:
            if not rec.folio_id:
                rec.folio_id = self.env['next.folio'].create({
                    'reservation_id': rec.id,
                    'partner_id': rec.partner_id.id,
                    'property_id': rec.property_id.id,
                })
        return records

    @api.depends('date_from', 'date_to')
    def _compute_nights(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.nights = max((rec.date_to - rec.date_from).days, 0)
            else:
                rec.nights = 0

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to <= rec.date_from:
                raise ValidationError('Check-out must be after check-in.')

    @api.constrains('room_ids', 'date_from', 'date_to', 'state')
    def _check_no_double_booking(self):
        """Defensive ORM-level guard. next_channel_manager adds a concurrency-safe
        availability ledger with row-level locking for the real race-condition
        protection across website/walk-in/OTA channels; this constraint is the
        last line of defense inside next_base itself."""
        for rec in self:
            if rec.state == 'cancelled' or not rec.room_ids:
                continue
            for room in rec.room_ids:
                conflicting = self.search_count([
                    ('id', '!=', rec.id),
                    ('room_ids', 'in', room.id),
                    ('state', 'not in', ('cancelled',)),
                    ('date_from', '<', rec.date_to),
                    ('date_to', '>', rec.date_from),
                ])
                if conflicting:
                    raise ValidationError(
                        'Room %s is already reserved for an overlapping date range.' % room.display_name)

    def action_confirm(self):
        self.write({'state': 'confirmed'})
        for room in self.room_ids:
            if room.status == 'green_ready':
                room.write({'status': 'blue_pending_checkin'})

    def action_check_in(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError('Only confirmed reservations can be checked in.')
            rec.write({'state': 'checked_in', 'actual_checkin': fields.Datetime.now()})
            rec.room_ids.write({'status': 'yellow_occupied'})

    def action_check_out(self):
        """Front-desk module wraps this with the mandatory inventory
        reconciliation wizard before allowing the call to go through."""
        for rec in self:
            if rec.state != 'checked_in':
                raise UserError('Only checked-in reservations can be checked out.')
            rec.write({'state': 'checked_out', 'actual_checkout': fields.Datetime.now()})
            rec.room_ids.write({'status': 'red_pending_checkout'})
            rec.folio_id.action_finalize()

    def action_cancel(self):
        for rec in self:
            if rec.state in ('checked_in', 'checked_out'):
                raise UserError('Cannot cancel a reservation that has already checked in.')
            rec.write({'state': 'cancelled'})
            for room in rec.room_ids:
                if room.status == 'blue_pending_checkin':
                    room.write({'status': 'green_ready'})
