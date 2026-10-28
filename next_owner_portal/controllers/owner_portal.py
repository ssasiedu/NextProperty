# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


def _parse_datetime_local(value):
    """<input type="datetime-local"> posts "YYYY-MM-DDTHH:MM" (an ISO 'T'
    separator, no seconds) - Odoo's Datetime field expects a "YYYY-MM-DD
    HH:MM:SS" string and raises (uncaught, surfacing as a 500) on anything
    else. Browsers also send different precision (sometimes ":SS" is
    already included), so this normalizes either form rather than assuming
    one shape."""
    if not value:
        return False
    value = value.replace('T', ' ')
    if len(value) == 16:  # "YYYY-MM-DD HH:MM", no seconds
        value += ':00'
    return value


def _build_trend_chart(points, currency_symbol):
    """points: ordered [(label, amount), ...], already aggregated to one
    point per period (never one per statement - an owner with several
    rooms can have more than one published statement for the same
    period, which isn't a second point on a trend, it's the same period
    counted twice). Returns everything the SVG in the template needs
    already computed - coordinates, the line/area point strings, grid
    lines - so the template only has to render values, never calculate
    with them (QWeb has no real arithmetic to lean on for this)."""
    if not points:
        return None
    width, height = 640, 220
    pad_x, pad_top, pad_bottom = 28, 20, 30
    plot_w = width - 2 * pad_x
    plot_h = height - pad_top - pad_bottom

    amounts = [p[1] for p in points]
    # The baseline always includes 0 - a trend of entirely-positive figures
    # shouldn't make the smallest one look like it's near the floor when
    # it's actually most of the way up a y-axis that doesn't start at 0.
    lo, hi = min(0.0, min(amounts)), max(0.0, max(amounts))
    span = (hi - lo) or 1.0

    def x_for(i):
        return pad_x if len(points) == 1 else pad_x + i * plot_w / (len(points) - 1)

    def y_for(v):
        return pad_top + (1 - (v - lo) / span) * plot_h

    coords = [(x_for(i), y_for(a)) for i, a in enumerate(amounts)]
    baseline_y = y_for(lo)

    if len(coords) == 1:
        # A single point still needs to read as a short flat segment, or
        # there's nothing for the area fill to enclose and nothing to see.
        x, y = coords[0]
        coords = [(x - 40, y), (x + 40, y)]

    line_points = ' '.join('%.1f,%.1f' % c for c in coords)
    area_points = '%s %.1f,%.1f %.1f,%.1f' % (
        line_points, coords[-1][0], baseline_y, coords[0][0], baseline_y)

    return {
        'width': width, 'height': height,
        'line_points': line_points,
        'area_points': area_points,
        'gridlines_y': [pad_top, pad_top + plot_h / 2, pad_top + plot_h],
        'points': [{
            'x': x_for(i), 'y': y_for(amounts[i]),
            'label': points[i][0],
            'amount_label': '%s %s' % (currency_symbol, '{:,.0f}'.format(amounts[i])),
        } for i in range(len(points))],
    }


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
        # A statement's room_id is blank for a property-wide figure (shown
        # to every co-owner of that property) or set for a single room's
        # figure (shown only to whichever co-owner actually owns that
        # room - see rule_next_room_owner's docstring for why a property
        # can have several co-owners splitting it room-by-room). Filtering
        # here, not just relying on the ir.rule on next.room, is what
        # stops this list from even listing a room-specific statement for
        # a room this owner can't see - rendering it would 403 on
        # st.room_id.name in the template.
        statements = request.env['next.owner.net.revenue'].search([
            ('property_id', 'in', partner.owned_property_ids.ids),
            '|', ('room_id', '=', False), ('room_id', 'in', partner.owned_room_ids.ids),
            ('state', '=', 'published'),
        ], order='period_year desc, period_month desc')
        # One point per PERIOD, not per statement - an owner who co-owns
        # several rooms can have more than one published statement for the
        # same month (one per room, or one per room plus a property-wide
        # one), which is the same period on a trend, not two separate
        # ones. Summed, then chronological order (oldest to newest) - the
        # table above stays newest-first, which is what someone checking a
        # specific month wants, but a trend reads left-to-right in time.
        period_totals = {}
        for s in statements:
            key = (int(s.period_year), int(s.period_month))
            period_totals.setdefault(key, {'label': '%s/%s' % (s.period_month, s.period_year), 'amount': 0.0})
            period_totals[key]['amount'] += s.amount
        ordered = [period_totals[key] for key in sorted(period_totals)]
        currency_symbol = request.env.company.currency_id.symbol or ''
        trend_chart = _build_trend_chart(
            [(p['label'], p['amount']) for p in ordered], currency_symbol)
        return request.render('next_owner_portal.owner_portal_net_revenue', {
            'statements': statements, 'trend_chart': trend_chart,
        })

    @http.route('/my/owner/net-revenue/<int:statement_id>/confirm', type='http', auth='user',
                website=True, methods=['POST'])
    def owner_confirm_payment(self, statement_id, **kw):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        statement = request.env['next.owner.net.revenue'].sudo().browse(statement_id)
        # Ownership check done here, explicitly, before the sudo() call that
        # follows - the method itself trusts its caller to have done this.
        if statement.property_id.id not in partner.owned_property_ids.ids or statement.payment_state != 'paid':
            return request.redirect('/my/owner/net-revenue')
        statement.action_owner_confirm_payment()
        return request.redirect('/my/owner/net-revenue')

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
            property_id = int(post.get('property_id') or 0)
            # sudo() below bypasses next.property's own ir.rule, so this
            # check is the only thing stopping a request for a property
            # this owner doesn't actually own from ever reaching create().
            if property_id not in partner.owned_property_ids.ids:
                return request.redirect('/my/owner/viewings')
            request.env['next.property.viewing'].sudo().create({
                'property_id': property_id,
                'owner_id': partner.id,
                'purpose': post.get('purpose', 'routine_inspection'),
                'date_start': _parse_datetime_local(post.get('date_start')),
                'date_end': _parse_datetime_local(post.get('date_end')),
                'notes': post.get('notes'),
            })
            return request.redirect('/my/owner/viewings')
        viewings = request.env['next.property.viewing'].search([('owner_id', '=', partner.id)])
        return request.render('next_owner_portal.owner_portal_viewings', {
            'viewings': viewings, 'properties': partner.owned_property_ids,
        })
