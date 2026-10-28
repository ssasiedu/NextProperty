# -*- coding: utf-8 -*-
from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """Covers the ordering where a partner is already marked
        is_property_owner and a res.users for them is then created
        directly (bulk import, XML-RPC, etc.) with no further write() to
        react to. Safe even when portal access is granted moments later
        via the wizard below, since write() re-checks and is idempotent."""
        users = super().create(vals_list)
        users._sync_owner_group_onto_self()
        return users

    def write(self, vals):
        """Grant Portal Access (portal.wizard.user.action_grant_access) sets
        the Role itself - base.group_portal - via a SEPARATE write() call
        made strictly after the user is created, not through res.partner at
        all (see portal_wizard.py: user_sudo.write({'active': True,
        'group_ids': [(4, group_portal.id), (3, group_public.id)]})). A
        create()-time sync (what this used to be) runs too early - before
        that write - so the Property Owner group got applied to an account
        that didn't have a Role yet, and if anything about the surrounding
        request then failed or retried, the account could be left with our
        group but no Role at all. Hooking THIS write() instead, and folding
        our own addition into the tail end of the very same group_ids
        change, guarantees the Owner group is only ever touched together
        with (never ahead of, never racing) the Role being established."""
        res = super().write(vals)
        if 'group_ids' in vals and not self.env.context.get('_skip_next_owner_group_sync'):
            self._sync_owner_group_onto_self()
        return res

    def _sync_owner_group_onto_self(self):
        group = self.env.ref('next_base.group_next_property_owner', raise_if_not_found=False)
        if not group:
            return
        # Idempotency check (group already present/absent as it should be)
        # both skips needless writes and - critically - is what stops the
        # inner write() below from recursing forever back into write().
        to_add = self.filtered(lambda u: u.partner_id.is_property_owner and group.id not in u.group_ids.ids)
        to_remove = self.filtered(lambda u: not u.partner_id.is_property_owner and group.id in u.group_ids.ids)
        if to_add:
            to_add.sudo().with_context(_skip_next_owner_group_sync=True).write({'group_ids': [(4, group.id)]})
        if to_remove:
            to_remove.sudo().with_context(_skip_next_owner_group_sync=True).write({'group_ids': [(3, group.id)]})
