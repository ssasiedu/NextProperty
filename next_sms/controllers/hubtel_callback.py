# -*- coding: utf-8 -*-
import json

from odoo import http
from odoo.http import request


class NextSmsHubtelCallback(http.Controller):
    """Hubtel posts delivery reports to this endpoint
    (next.sms.provider.callback_url). Updates the matching next.sms.log by
    provider_message_id. Never raises - a malformed or unexpected callback
    payload is logged and acknowledged with 200 so Hubtel doesn't retry
    indefinitely."""

    @http.route('/next_sms/hubtel/delivery_report', type='json', auth='public', csrf=False, methods=['POST'])
    def delivery_report(self, **kw):
        try:
            payload = json.loads(request.httprequest.data or b'{}')
        except Exception:
            payload = kw or {}

        message_id = payload.get('messageId') or payload.get('MessageId')
        status = (payload.get('status') or payload.get('Status') or '').lower()

        if message_id:
            log = request.env['next.sms.log'].sudo().search(
                [('provider_message_id', '=', message_id)], limit=1)
            if log:
                from odoo import fields
                vals = {}
                if status in ('delivered', 'delivrd'):
                    vals = {'status': 'delivered', 'delivered_date': fields.Datetime.now()}
                elif status in ('failed', 'undelivered', 'rejected'):
                    vals = {'status': 'failed', 'error_message': payload.get('reason') or status}
                if vals:
                    log.write(vals)
        return {'received': True}
