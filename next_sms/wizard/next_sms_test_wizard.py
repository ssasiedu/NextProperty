# -*- coding: utf-8 -*-
from odoo import fields, models


class NextSmsTestWizard(models.TransientModel):
    """Lets a manager fire a one-off SMS straight at the configured Hubtel
    provider, synchronously, to confirm the gateway/credentials/sender ID
    actually work - without touching next.sms.log, the async queue, or
    needing a real guest/owner partner record to test against. Opened from
    SMS > Test SMS Gateway, or the "Send Test SMS" button on a provider
    record (pre-filled with that provider)."""
    _name = 'next.sms.test.wizard'
    _description = 'Test SMS Gateway'

    provider_id = fields.Many2one(
        'next.sms.provider', string='SMS Provider', required=True,
        default=lambda self: self.env['next.sms.provider']._get_provider())
    to_number = fields.Char(
        string='Phone Number', required=True,
        help='Full international format (E164), e.g. +233241234567.')
    message = fields.Text(
        required=True, default='This is a test message from NEXT Property Management.')

    result_status = fields.Selection([('sent', 'Sent'), ('failed', 'Failed')], readonly=True)
    result_detail = fields.Text(readonly=True)

    def action_send_test(self):
        self.ensure_one()
        if not self.provider_id:
            self.write({
                'result_status': 'failed',
                'result_detail': 'No SMS provider configured. Create one under SMS > Providers first.',
            })
        else:
            result = self.provider_id._send(self.to_number, self.message)
            if result.get('status') == 'sent':
                self.write({
                    'result_status': 'sent',
                    'result_detail': 'Sent successfully via "%s". Provider message ID: %s%s' % (
                        self.provider_id.name,
                        result.get('provider_message_id') or '(none returned)',
                        ' | Rate: %s' % result.get('cost') if result.get('cost') is not None else '',
                    ),
                })
            else:
                self.write({
                    'result_status': 'failed',
                    'result_detail': result.get('error') or 'Unknown error.',
                })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'next.sms.test.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
