# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextRoom(models.Model):
    """A sellable room belonging to a property and room type.

    `status` drives the colour-coded dashboards used throughout the suite
    (Front Desk kanban, Housekeeping kanban, Owner Portal live status):

    * blue_pending_checkin  - reserved, guest not yet arrived
    * yellow_occupied       - guest currently in-house
    * red_pending_checkout  - checked out, awaiting housekeeping
    * green_ready           - clean and available to sell
    * grey_blocked          - blocked (maintenance, owner viewing, manual hold)
    """
    _name = 'next.room'
    _description = 'Room'
    _inherit = ['mail.thread']
    _order = 'property_id, name'

    name = fields.Char(string='Room Number/Name', required=True, tracking=True)
    property_id = fields.Many2one('next.property', required=True, ondelete='cascade', tracking=True)
    room_type_id = fields.Many2one('next.room.type', string='Room Type', required=True,
                                    domain="[('property_id', '=', property_id)]", tracking=True)
    floor = fields.Char()

    status = fields.Selection([
        ('blue_pending_checkin', 'Pending Check-in'),
        ('yellow_occupied', 'Occupied'),
        ('red_pending_checkout', 'Pending Checkout / Dirty'),
        ('green_ready', 'Ready / Available'),
        ('grey_blocked', 'Blocked'),
    ], default='green_ready', required=True, tracking=True, copy=False)

    status_color = fields.Char(compute='_compute_status_color', store=False)

    owner_id = fields.Many2one('res.partner', string='Owner', domain=[('is_property_owner', '=', True)],
                                help='Property owner this room belongs to, for Owner Portal scoping.')

    qr_code = fields.Binary(string='QR Code', copy=False, attachment=True,
                             help='Auto-generated QR code linking to this room\'s self-order page '
                                  '(see next_pos_integration).')
    qr_code_url = fields.Char(string='QR Target URL', copy=False)

    active = fields.Boolean(default=True)
    notes = fields.Text()

    blocked_reason = fields.Char(help='Why this room is currently grey_blocked (maintenance, viewing, manual).')

    _name_property_uniq = models.Constraint(
        'unique(name, property_id)',
        'Room number must be unique within a property.',
    )

    _STATUS_COLORS = {
        'blue_pending_checkin': '#3B82F6',
        'yellow_occupied': '#F59E0B',
        'red_pending_checkout': '#EF4444',
        'green_ready': '#22C55E',
        'grey_blocked': '#9CA3AF',
    }

    def _compute_status_color(self):
        for rec in self:
            rec.status_color = self._STATUS_COLORS.get(rec.status, '#9CA3AF')

    def action_set_blocked(self, reason=False):
        self.write({'status': 'grey_blocked', 'blocked_reason': reason or ''})

    def action_clear_block(self):
        """Release a grey_blocked room back to ready. Callers (maintenance,
        owner viewing) should check no other hold applies before calling this."""
        self.write({'status': 'green_ready', 'blocked_reason': False})

    def is_blocked_for_booking(self, date_from, date_to):
        """Returns True if this room cannot be booked for the given range:
        manually blocked, or has a conflicting reservation/maintenance hold.
        next_channel_manager further layers an availability ledger on top of this."""
        self.ensure_one()
        if self.status == 'grey_blocked':
            return True
        Reservation = self.env['next.reservation']
        conflicting = Reservation.search_count([
            ('room_ids', 'in', self.id),
            ('state', 'not in', ('cancelled',)),
            ('date_from', '<', date_to),
            ('date_to', '>', date_from),
        ])
        return bool(conflicting)
