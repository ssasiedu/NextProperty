# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """Covers the other ordering from res.partner's own create()/write()
        sync (see res_partner.py): a partner is marked is_property_owner
        first, and only later actually granted portal access (Settings >
        Users > "Grant Portal Access", or any other flow that creates a
        res.users for an existing partner). That path creates the
        res.users record directly - it never calls res.partner.write() -
        so without this, the new portal account would be marked an owner
        on the contact form but silently missing the Property Owner group
        that the Owner Portal and its backend access actually depend on."""
        users = super().create(vals_list)
        users.mapped('partner_id')._sync_owner_group()
        return users
