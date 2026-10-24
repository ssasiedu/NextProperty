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

    api_base_url = fields.Char(default='https://smsc.hubtel.com/v1/messages/send',
                                help="Hubtel's Quick Send (GET) endpoint. Host is smsc.hubtel.com, "
                                     "not sms.hubtel.com - double-check this if messages are failing.")

    def _compute_callback_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if not rec.callback_url:
                rec.callback_url = '%s/next_sms/hubtel/delivery_report' % base

    def action_open_test_wizard(self):
        """"Send Test SMS" button on the provider form - opens the test
        wizard pre-filled with this provider so a manager can confirm
        credentials/host/sender ID work before relying on it for real
        guest/owner notifications."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Test SMS Gateway',
            'res_model': 'next.sms.test.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_provider_id': self.id},
        }

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
        """Hubtel "Quick Send" (GET, no auth header) - see
        https://developers.hubtel.com SMS API docs. Response on success is
        JSON: {rate, messageId, status: 0, statusDescription, networkId}.
        A non-zero `status`, a non-200 HTTP code, or a non-JSON body (e.g. an
        HTML error page from a wrong host) are all treated as failures."""
        import requests
        if not self.client_id or not self.client_secret or not self.sender_id:
            return {'status': 'failed',
                    'error': 'Missing client_id/client_secret/sender_id on SMS provider "%s".' % self.name}
        if not self.api_base_url:
            return {'status': 'failed', 'error': 'SMS provider "%s" has no API base URL configured.' % self.name}
        try:
            resp = requests.get(self.api_base_url, params={
                'clientid': self.client_id,
                'clientsecret': self.client_secret,
                'from': self.sender_id,
                'to': to_number,
                'content': message,
            }, timeout=15)
        except Exception as exc:  # noqa: broad-except - network/DNS/timeout errors
            return {'status': 'failed', 'error': 'Could not reach Hubtel: %s' % exc}

        try:
            data = resp.json() if resp.content else {}
        except ValueError:
            # Non-JSON body usually means the wrong host/URL (e.g. an HTML
            # error page) rather than a real Hubtel API error.
            return {'status': 'failed',
                    'error': 'Hubtel returned a non-JSON response (HTTP %s). Double-check api_base_url. '
                              'Body (truncated): %s' % (resp.status_code, resp.text[:300])}

        # Hubtel returns HTTP 201 (not 200) on a successful send - the real
        # success signal is `status: 0` in the JSON body. Accept any 2xx.
        if resp.ok and data.get('status') == 0:
            return {
                'status': 'sent',
                'provider_message_id': data.get('messageId'),
                'cost': data.get('rate'),
            }
        return {'status': 'failed',
                'error': 'HTTP %s: %s' % (resp.status_code, data.get('statusDescription') or data)}
