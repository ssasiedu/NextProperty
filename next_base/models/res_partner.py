# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_property_owner = fields.Boolean(
        string='Is Property Owner', default=False,
        help='Marks this contact as a property owner. Combined with "Owned '
             'Properties"/"Owned Rooms" below and Portal Access (Action > '
             'Grant Portal Access), this is all that is needed to give them '
             'the Owner Portal: no Internal User / extra license required, '
             'and the Property Owner access group is granted and revoked '
             'automatically as this checkbox changes - nothing to set by '
             'hand under Settings > Users.')

    owned_property_ids = fields.Many2many(
        'next.property', 'next_property_owner_rel', 'partner_id', 'property_id',
        string='Owned Properties')

    # Not a plain One2many on next.room.owner_id any more: a room counts as
    # owned here on the same EXCLUSIVE-fallback condition as
    # rule_next_room_owner in next_base_security.xml (keep both in sync if
    # either ever changes): owner_id = me, OR owner_id is unset AND its
    # property is one of mine. Exclusive, not a plain OR, because a
    # property can have several co-owners each owning specific rooms
    # within it (e.g. Roxy Hotel: owner_ids [ROXYMAN, NANA], with
    # 101/201 individually owner_id=ROXYMAN and 102/301 owner_id=NANA) -
    # a plain OR would show every co-owner every room of any property
    # they co-own, defeating the whole point of setting owner_id per room.
    # The property-level fallback only ever applies when a room has no
    # individual owner recorded at all (the common single-owner case,
    # where nobody bothers setting owner_id per room).
    owned_room_ids = fields.Many2many(
        'next.room', compute='_compute_owned_room_ids', string='Owned Rooms')

    @api.depends('is_property_owner', 'owned_property_ids', 'owned_property_ids.room_ids',
                 'owned_property_ids.room_ids.owner_id')
    def _compute_owned_room_ids(self):
        Room = self.env['next.room']
        for partner in self:
            if not partner.is_property_owner:
                partner.owned_room_ids = Room
                continue
            partner.owned_room_ids = Room.search([
                '|',
                ('owner_id', '=', partner.id),
                '&', ('owner_id', '=', False), ('property_id.owner_ids', 'in', partner.id),
            ])

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._sync_owner_group()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if 'is_property_owner' in vals:
            self._sync_owner_group()
        return res

    @api.model
    def _find_or_create_guest(self, name, email=None, phone=None):
        """Resolves (or creates) the plain contact behind a reservation's
        partner_id from details collected at booking time - the website's
        guest-details step, an OTA payload, etc. Matched by email first so
        a repeat guest doesn't end up with a new duplicate contact every
        time they book. Deliberately generic (not tied to any one booking
        channel) so next_channel_manager's OTA guest resolution and
        next_booking's website guest-details step both go through this one
        place rather than drifting apart."""
        partner = self.browse()
        if email:
            partner = self.search([('email', '=', email)], limit=1)
        if not partner:
            partner = self.create({'name': name or 'Guest', 'email': email, 'phone': phone})
        return partner

    def _sync_owner_group(self):
        """Keep every linked user's Property Owner group membership in
        lockstep with is_property_owner, so marking a customer as an owner
        (and nothing else - no manual group-ticking, no Internal User
        license) is what grants them the Owner Portal and its backend
        read access: every related ir.model.access.csv row and ir.rule in
        next_base_security.xml is gated on this one group. The actual
        group write lives on res.users (_sync_owner_group_onto_self) -
        that's also the method res.users' own write()/create() hooks call,
        so there is exactly one place that ever touches this group,
        whichever side (partner flag, or portal-access grant) changed."""
        self.mapped('user_ids')._sync_owner_group_onto_self()

    sms_opt_in = fields.Boolean(
        string='SMS Opt-in', default=True,
        help='If disabled, next_sms will never send this contact a message, '
             'regardless of template triggers.')

    email_opt_in = fields.Boolean(
        string='Email Opt-in', default=True,
        help='If disabled, next_sms will never email this contact, '
             'regardless of template triggers.')

