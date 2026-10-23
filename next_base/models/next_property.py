# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextProperty(models.Model):
    """A physical property (hotel / guesthouse / apartment block) managed by
    the NEXT Property Management suite. Every room, reservation, folio and
    owner-facing record is ultimately scoped to one `next.property`.
    """
    _name = 'next.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(help='Short code used in sequences, QR payloads, etc.', copy=False)
    active = fields.Boolean(default=True)

    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')

    tz = fields.Selection('_tz_get', string='Timezone', default=lambda self: self.env.user.tz or 'UTC')
    currency_id = fields.Many2one('res.currency', required=True,
                                   default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    owner_ids = fields.Many2many(
        'res.partner', 'next_property_owner_rel', 'property_id', 'partner_id',
        string='Owners', domain=[('is_property_owner', '=', True)],
        help='Property owners with portal access scoped to this property.')

    manager_id = fields.Many2one('res.users', string='Property/Hotel Manager')

    room_type_ids = fields.One2many('next.room.type', 'property_id', string='Room Types')
    room_ids = fields.One2many('next.room', 'property_id', string='Rooms')
    room_count = fields.Integer(compute='_compute_room_count')

    single_property_deployment = fields.Boolean(
        compute='_compute_single_property_deployment',
        help='True when this is the only active property - used by the booking '
             'website to skip the "select a property" step.')

    @api.model
    def _tz_get(self):
        return [(tz, tz) for tz in sorted(__import__('pytz').all_timezones)]

    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)

    def _compute_single_property_deployment(self):
        total = self.search_count([('active', '=', True)])
        for rec in self:
            rec.single_property_deployment = total <= 1

    _code_company_uniq = models.Constraint(
        'unique(code, company_id)',
        'Property code must be unique per company.',
    )
