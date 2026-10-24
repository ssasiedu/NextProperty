# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class NextSmsQueue(models.Model):
    """Asynchronous dispatch layer so no checkout/booking transaction ever
    blocks waiting on the Hubtel API.

    If the OCA `queue_job` module is installed, `_enqueue` delegates to it
    via `with_delay()` and this model's cron is a no-op safety net. If
    `queue_job` is NOT installed, `_enqueue` just marks the log 'queued' (the
    default) and a short-interval `ir.cron` (see data/next_sms_cron.xml)
    picks up queued logs and sends them in small batches - still
    asynchronous from the caller's point of view, since the cron runs in its
    own transaction after the triggering request has already committed/
    returned."""
    _name = 'next.sms.queue'
    _description = 'SMS Dispatch Queue (queue_job fallback)'

    def _has_queue_job(self):
        return 'queue.job' in self.env

    def _enqueue(self, log):
        if self._has_queue_job():
            self.env['next.sms.log'].with_delay(description='Send SMS log #%s' % log.id)._dispatch_one(log.id)
        # else: nothing to do now - the cron fallback below will pick it up.

    @api.model
    def _cron_dispatch_queued(self, batch_size=50):
        if self._has_queue_job():
            return  # queue_job handles dispatch; this cron is the fallback only.
        logs = self.env['next.sms.log'].search([('status', '=', 'queued')], limit=batch_size)
        for log in logs:
            log._dispatch_one(log.id)


class NextSmsLogDispatch(models.Model):
    """Dispatch logic lives on next.sms.log itself so `with_delay()` (when
    queue_job is present) can target it directly as a recordset method."""
    _inherit = 'next.sms.log'

    def _dispatch_one(self, log_id):
        log = self.browse(log_id)
        if not log.exists() or log.status != 'queued':
            return
        provider = self.env['next.sms.provider']._get_provider(property_id=log.property_id.id)
        if not provider:
            log.write({'status': 'failed', 'error_message': 'No active SMS provider configured.'})
            _logger.warning('next_sms: no provider configured for property %s', log.property_id.display_name)
            return

        result = provider._send(log.to_number, log.message, log=log)
        if result.get('status') == 'sent':
            log.write({
                'status': 'sent',
                'provider_message_id': result.get('provider_message_id'),
                'cost': result.get('cost') or 0.0,
                'sent_date': fields.Datetime.now(),
            })
        else:
            log.write({'status': 'failed', 'error_message': result.get('error')})
