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
    owned_room_ids = fields.One2many('next.room', 'owner_id', string='Owned Rooms')

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

    def _sync_owner_group(self):
        """Keep every linked user's Property Owner group membership in
        lockstep with is_property_owner, so marking a customer as an owner
        (and nothing else - no manual group-ticking, no Internal User
        license) is what grants them the Owner Portal and its backend
        read access: every related ir.model.access.csv row and ir.rule in
        next_base_security.xml is gated on this one group. Also called
        from res.users' own create() override, so the sync happens
        correctly whichever order the two steps occur in: marking an
        existing portal user as owner, or granting portal access
        afterwards to a partner already marked as owner."""
        group = self.env.ref('next_base.group_next_property_owner', raise_if_not_found=False)
        if not group:
            return
        for partner in self:
            users = partner.user_ids
            if not users:
                continue
            if partner.is_property_owner:
                users.sudo().write({'groups_id': [(4, group.id)]})
            else:
                users.sudo().write({'groups_id': [(3, group.id)]})

    sms_opt_in = fields.Boolean(
        string='SMS Opt-in', default=True,
        help='If disabled, next_sms will never send this contact a message, '
             'regardless of template triggers.')

    email_opt_in = fields.Boolean(
        string='Email Opt-in', default=True,
        help='If disabled, next_sms will never email this contact, '
             'regardless of template triggers.')

