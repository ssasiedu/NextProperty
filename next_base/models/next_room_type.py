# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextRoomType(models.Model):
    _name = 'next.room.type'
    _description = 'Room Type'
    _inherit = ['mail.thread']
    _order = 'property_id, sequence, name'

    name = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10)
    property_id = fields.Many2one('next.property', string='Property', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='property_id.company_id', store=True)
    currency_id = fields.Many2one(related='property_id.currency_id', store=True)

    # Pricing
    list_price = fields.Monetary(string='Standard Nightly Rate', required=True)
    weekend_price = fields.Monetary(string='Weekend Nightly Rate',
                                     help='Leave 0 to always use the standard rate.')
    extra_adult_price = fields.Monetary(string='Extra Adult Surcharge')
    extra_child_price = fields.Monetary(string='Extra Child Surcharge')

    # Capacity
    max_adults = fields.Integer(default=2, required=True)
    max_children = fields.Integer(default=0)
    base_occupancy = fields.Integer(default=2, help='Occupancy included in the standard rate.')

    # Amenities / media
    amenity_ids = fields.Many2many('next.room.amenity', string='Amenities')
    image_1920 = fields.Image(string='Main Photo', max_width=1920, max_height=1920)
    photo_ids = fields.One2many('next.room.type.photo', 'room_type_id', string='Photo Gallery')

    description = fields.Html(string='Website Description')
    active = fields.Boolean(default=True)

    room_ids = fields.One2many('next.room', 'room_type_id', string='Rooms')
    room_count = fields.Integer(compute='_compute_room_count')

    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)

    def _max_occupancy(self):
        self.ensure_one()
        return self.max_adults + self.max_children


class NextRoomAmenity(models.Model):
    _name = 'next.room.amenity'
    _description = 'Room Amenity'
    _order = 'name'

    name = fields.Char(required=True)
    icon = fields.Char(help='Optional icon class (e.g. fa-wifi) for website display.')


class NextRoomTypePhoto(models.Model):
    _name = 'next.room.type.photo'
    _description = 'Room Type Photo'
    _order = 'sequence'

    sequence = fields.Integer(default=10)
    room_type_id = fields.Many2one('next.room.type', required=True, ondelete='cascade')
    image = fields.Image(max_width=1920, max_height=1920, required=True)
    name = fields.Char(string='Caption')
