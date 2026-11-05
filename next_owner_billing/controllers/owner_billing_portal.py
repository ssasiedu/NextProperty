# -*- coding: utf-8 -*-
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request


class NextOwnerBillingPortal(http.Controller):
    """Owner-facing service-charge billing pages. Same trust boundary as
    next_owner_portal's own controller: every query/write is scoped to the
    logged-in owner's partner, with sudo() used only after an explicit
    ownership check - never trusting a client-supplied id beyond that."""

    def _owner_or_redirect(self):
        partner = request.env.user.partner_id
        if not partner.is_property_owner:
            return None
        return partner

    @http.route('/my/owner/billing', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def owner_billing(self, **post):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        if request.httprequest.method == 'POST':
            bill_id = int(post.get('bill_id') or 0)
            bill = request.env['next.owner.bill'].sudo().browse(bill_id)
            if bill.owner_id.id == partner.id:
                amount = float(post.get('amount') or 0.0)
                if amount > 0:
                    try:
                        bill.action_report_payment(
                            amount=amount, reference=post.get('reference'),
                            payment_date=post.get('payment_date') or None)
                    except UserError:
                        pass  # e.g. already fully paid / not issued - nothing to report.
            return request.redirect('/my/owner/billing')
        bills = request.env['next.owner.bill'].sudo().search(
            [('owner_id', '=', partner.id), ('state', '=', 'issued')])
        return request.render('next_owner_billing.portal_owner_billing', {
            'bills': bills, 'balance': partner.owner_billing_balance,
        })

    @http.route('/my/owner/billing/statement', type='http', auth='user', website=True)
    def owner_billing_statement(self, **kw):
        partner = self._owner_or_redirect()
        if not partner:
            return request.redirect('/my')
        pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'next_owner_billing.report_next_owner_bill_statement', [partner.id])
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename="Service Charge Statement.pdf"'),
        ])
