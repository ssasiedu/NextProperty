# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import http
from odoo.http import request


class NextHousekeepingWorkerPortal(http.Controller):
    """Lightweight self-service page for a housekeeping worker who is a
    PORTAL user, not a full internal user (see next_base's security
    groups) - just enough to see what's assigned to them and tap
    Start/Complete, without ever touching the backend Kanban. Every write
    here goes through sudo() after an explicit ownership check, the same
    pattern next_booking/next_owner_portal already use for guest/owner
    writes - a portal worker generally has no direct write ACL on the
    model itself."""

    @http.route(['/my/worker/housekeeping'], type='http', auth='user', website=True)
    def worker_housekeeping_dashboard(self, date_from=None, date_to=None, **kw):
        user = request.env.user
        Task = request.env['next.housekeeping.task'].sudo()
        domain = [('assigned_to', '=', user.id)]
        period_domain = []
        if date_from:
            period_domain.append(('create_date', '>=', date_from))
        if date_to:
            period_domain.append(('create_date', '<=', date_to + ' 23:59:59'))

        all_tasks = Task.search(domain + period_domain, order='create_date desc')
        counts = {
            'total': len(all_tasks),
            'not_started': len(all_tasks.filtered(lambda t: t.state == 'not_started')),
            'in_progress': len(all_tasks.filtered(lambda t: t.state == 'in_progress')),
            'complete': len(all_tasks.filtered(lambda t: t.state in ('inspected', 'complete'))),
        }
        return request.render('next_housekeeping.worker_portal_dashboard', {
            'tasks': all_tasks, 'counts': counts,
            'date_from': date_from or '', 'date_to': date_to or '',
        })

    @http.route(['/my/worker/housekeeping/<int:task_id>/start'], type='http', auth='user',
                website=True, methods=['POST'])
    def worker_housekeeping_start(self, task_id, **kw):
        task = request.env['next.housekeeping.task'].sudo().browse(task_id)
        if task.assigned_to.id == request.env.user.id and task.state == 'not_started':
            task.action_start()
        return request.redirect('/my/worker/housekeeping')

    @http.route(['/my/worker/housekeeping/<int:task_id>/complete'], type='http', auth='user',
                website=True, methods=['POST'])
    def worker_housekeeping_complete(self, task_id, **kw):
        task = request.env['next.housekeeping.task'].sudo().browse(task_id)
        if task.assigned_to.id == request.env.user.id and task.state == 'in_progress':
            task.action_complete()
        return request.redirect('/my/worker/housekeeping')
