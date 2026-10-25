# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class NextMaintenanceWorkerPortal(http.Controller):
    """Same shape as next_housekeeping's worker portal: a lightweight
    self-service page for a Maintenance Officer who is a PORTAL user, not
    a full internal user. Every write goes through sudo() after an
    explicit ownership check."""

    @http.route(['/my/worker/maintenance'], type='http', auth='user', website=True)
    def worker_maintenance_dashboard(self, date_from=None, date_to=None, **kw):
        user = request.env.user
        Request = request.env['maintenance.request'].sudo()
        domain = [('assigned_officer_id', '=', user.id)]
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to + ' 23:59:59'))

        all_requests = Request.search(domain, order='create_date desc')
        counts = {
            'total': len(all_requests),
            'new': len(all_requests.filtered(lambda r: r.next_state in ('new', 'assigned'))),
            'in_progress': len(all_requests.filtered(lambda r: r.next_state == 'in_progress')),
            'done': len(all_requests.filtered(lambda r: r.next_state in ('resolved', 'verified'))),
        }
        return request.render('next_maintenance.worker_portal_dashboard', {
            'requests': all_requests, 'counts': counts,
            'date_from': date_from or '', 'date_to': date_to or '',
        })

    @http.route(['/my/worker/maintenance/<int:request_id>/start'], type='http', auth='user',
                website=True, methods=['POST'])
    def worker_maintenance_start(self, request_id, **kw):
        req = request.env['maintenance.request'].sudo().browse(request_id)
        if req.assigned_officer_id.id == request.env.user.id and req.next_state in ('new', 'assigned'):
            req.action_start_progress()
        return request.redirect('/my/worker/maintenance')

    @http.route(['/my/worker/maintenance/<int:request_id>/resolve'], type='http', auth='user',
                website=True, methods=['POST'])
    def worker_maintenance_resolve(self, request_id, **kw):
        req = request.env['maintenance.request'].sudo().browse(request_id)
        if req.assigned_officer_id.id == request.env.user.id and req.next_state == 'in_progress':
            req.action_resolve()
        return request.redirect('/my/worker/maintenance')
