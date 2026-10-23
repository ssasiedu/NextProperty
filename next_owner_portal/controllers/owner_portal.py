# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class NextOwnerPortal(CustomerPortal):
    """Owner-facing portal pages. All queries are scoped to the logged-in
    owner's partner via the record rules in next_base/next_owner_portal
    (never trust client-supplied ids beyond that scoping)."""

    def _owner_or_redirect(self):
        partner = request.env.user.partner_id
        if not partner.is_property_owner:
            return None
        return partner

    @http.route('/my/owner', type='http', auth='user', website=True)
    def owner_home(self, **kw):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        properties = partner.owned_property_ids
        return request.render('next_owner_portal.owner_portal_home', {'properties': properties})

    @http.route('/my/owner/net-revenue', type='http', auth='user', website=True)
    def owner_net_revenue(self, **kw):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        # Only ever the manually entered, published figure - never a
        # system-computed value - per the non-negotiable constraint.
        statements = request.env['next.owner.net.revenue'].search([
            ('property_id', 'in', partner.owned_property_ids.ids),
            ('state', '=', 'published'),
        ], order='period_year desc, period_month desc')
        return request.render('next_owner_portal.owner_portal_net_revenue', {'statements': statements})

    @http.route('/my/owner/rooms', type='http', auth='user', website=True)
    def owner_rooms(self, **kw):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        rooms = partner.owned_room_ids
        return request.render('next_owner_portal.owner_portal_rooms', {'rooms': rooms})

    @http.route(['/my/owner/viewings', '/my/owner/viewings/new'], type='http', auth='user',
                website=True, methods=['GET', 'POST'])
    def owner_viewings(self, **post):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        if request.httprequest.method == 'POST':
            request.env['next.property.viewing'].sudo().create({
                'property_id': int(post.get('property_id')),
                'owner_id': partner.id,
                'purpose': post.get('purpose', 'routine_inspection'),
                'date_start': post.get('date_start'),
                'date_end': post.get('date_end'),
                'notes': post.get('notes'),
            })
            return request.redirect('/my/owner/viewings')
        viewings = request.env['next.property.viewing'].search([('owner_id', '=', partner.id)])
        return request.render('next_owner_portal.owner_portal_viewings', {
            'viewings': viewings, 'properties': partner.owned_property_ids,
        })
