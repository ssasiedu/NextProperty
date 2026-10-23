# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextSmsProvider(models.Model):
    """Stores Hubtel credentials, configurable per company and/or property.
    The interface is deliberately provider-abstracted: business logic across
    the suite never calls Hubtel directly - it calls
    `next.sms.template.send_trigger(...)`, which resolves a provider and
    calls `provider._send(...)`. Swapping in a different provider later only
    means adding a new `provider_type` branch in `_send()`."""
    _name = 'next.sms.provider'
    _description = 'SMS Provider Configuration'

    name = fields.Char(required=True, default='Hubtel')
    provider_type = fields.Selection([('hubtel', 'Hubtel')], default='hubtel', required=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    property_id = fields.Many2one('next.property', string='Property',
                                   help='Leave empty to apply to all properties of this company.')

    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret')
    sender_id = fields.Char(string='Sender ID', help='Hubtel approved sender ID (max 11 chars).')
    callback_url = fields.Char(string='Delivery Report Callback URL',
                                compute='_compute_callback_url', store=True, readonly=False)
    active = fields.Boolean(default=True)

    api_base_url = fields.Char(default='https://sms.hubtel.com/v1/messages/send')

    def _compute_callback_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if not rec.callback_url:
                rec.callback_url = '%s/next_sms/hubtel/delivery_report' % base

    @api.model
    def _get_provider(self, property_id=False, company=None):
        company = company or self.env.company
        domain = [('active', '=', True), ('company_id', '=', company.id)]
        if property_id:
            provider = self.search(domain + [('property_id', '=', property_id)], limit=1)
            if provider:
                return provider
        return self.search(domain + [('property_id', '=', False)], limit=1)

    def _send(self, to_number, message, log=None):
        """Dispatches `message` to `to_number` via this provider. Returns a
        dict with at least {'provider_message_id': str|None, 'status': str}.
        Never raises on provider/API failure - failures are recorded on the
        log record so a flaky SMS gateway can never block the caller."""
        self.ensure_one()
        if self.provider_type == 'hubtel':
            return self._send_via_hubtel(to_number, message)
        return {'status': 'failed', 'error': 'Unsupported provider_type: %s' % self.provider_type}

    def _send_via_hubtel(self, to_number, message):
        import requests
        try:
            resp = requests.get(self.api_base_url, params={
                'clientid': self.client_id,
                'clientsecret': self.client_secret,
                'from': self.sender_id,
                'to': to_number,
                'content': message,
            }, timeout=10)
            data = resp.json() if resp.content else {}
            if resp.status_code == 200 and data.get('status') == 0:
                return {'status': 'sent', 'provider_message_id': data.get('messageId')}
            return {'status': 'failed', 'error': str(data)}
        except Exception as exc:  # noqa: broad-except - never let a gateway outage raise
            return {'status': 'failed', 'error': str(exc)}
