# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextServiceRequest(models.Model):
    """Guest-facing request raised from the portal during a stay: a fault
    report, a room-service request, or a general request. Visible to the
    guest with a live status; front desk/housekeeping/maintenance act on it
    (maintenance faults are typically escalated to next.maintenance.request
    by next_maintenance)."""
    _name = 'next.service.request'
    _description = 'Guest Service Request'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Subject', required=True)
    reservation_id = fields.Many2one('next.reservation', required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='reservation_id.partner_id', store=True)
    property_id = fields.Many2one(related='reservation_id.property_id', store=True)
    # A reservation can cover several rooms, but front desk/housekeeping
    # think in terms of "which room has the issue", not "which booking" -
    # the booking's first room is right for the overwhelming majority of
    # stays (one room), and is the same room action_acknowledge() below
    # already escalates a fault against.
    room_id = fields.Many2one(
        'next.room', compute='_compute_room_id', store=True, string='Room',
        help='The room this request is against - the reservation\'s first room.')
    partner_phone = fields.Char(
        compute='_compute_partner_phone', string='Guest Phone',
        help='So front desk/maintenance can call the guest back without opening the contact record.')

    @api.depends('reservation_id.room_ids')
    def _compute_room_id(self):
        for rec in self:
            rec.room_id = rec.reservation_id.room_ids[:1]

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_partner_phone(self):
        for rec in self:
            rec.partner_phone = rec.partner_id.phone or rec.partner_id.mobile

    request_type = fields.Selection([
        ('fault', 'Fault Report'),
        ('room_service', 'Room Service'),
        ('general', 'General Request'),
    ], required=True, default='general')

    description = fields.Text()

    status = fields.Selection([
        ('submitted', 'Submitted'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], default='submitted', required=True, tracking=True)

    maintenance_request_id = fields.Many2one('maintenance.request', string='Linked Maintenance Ticket',
                                              readonly=True, copy=False)

    def action_acknowledge(self):
        self.write({'status': 'acknowledged'})

    def action_start(self):
        self.write({'status': 'in_progress'})

    def action_resolve(self):
        self.write({'status': 'resolved'})
