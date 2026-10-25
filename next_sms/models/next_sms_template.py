# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

# The full trigger table from the specification. `code` is the stable
# technical key other modules call `send_trigger()` with; `label` and
# `default_body` seed the next_sms_templates.xml demo/default data.
TRIGGER_CODES = [
    ('booking_confirmation', 'Booking: Confirmation / Payment Received'),
    ('booking_reminder', 'Booking: Reminder (24h pre check-in)'),
    ('booking_cancellation', 'Booking: Cancellation Confirmation'),
    ('booking_deposit_received', 'Booking: Deposit/Advance Payment Received'),
    ('checkin_complete', 'Front Desk: Check-in Complete'),
    ('checkout_complete', 'Front Desk: Checkout Complete + Final Folio'),
    ('checkout_discrepancy', 'Front Desk: Inventory Discrepancy at Checkout'),
    ('qr_order_received', 'POS/QR: Order Received/Confirmed'),
    ('qr_order_ready', 'POS/QR: Order Ready / Service Complete'),
    ('housekeeping_room_ready', 'Housekeeping: Room Flipped to Green/Ready'),
    ('housekeeping_task_overdue', 'Housekeeping: Task Overdue'),
    ('maintenance_new_ticket', 'Maintenance: New Ticket Logged'),
    ('maintenance_status_update', 'Maintenance: Status Update'),
    ('owner_net_revenue_published', 'Owner Portal: New Net Revenue Statement Published'),
    ('owner_payment_made', 'Owner Portal: Net Revenue Payment Sent'),
    ('owner_payment_confirmed', 'Owner Portal: Owner Confirmed Payment Receipt'),
    ('owner_viewing_requested', 'Owner Portal: Viewing Requested'),
    ('owner_viewing_confirmed', 'Owner Portal: Viewing Confirmed/Rescheduled'),
    ('owner_room_status_change', 'Owner Portal: Room Status Change'),
    ('channel_ota_booking_received', 'Channel Manager: OTA Booking Received'),
    ('auth_otp', 'Auth: OTP/2FA for Owner/Guest Portal Login'),
]


class NextSmsTemplate(models.Model):
    _name = 'next.sms.template'
    _description = 'SMS Template'
    _order = 'trigger_code'

    name = fields.Char(required=True)
    trigger_code = fields.Selection(TRIGGER_CODES, required=True, index=True)
    property_id = fields.Many2one('next.property', string='Property',
                                   help='Leave empty to apply to all properties.')
    body = fields.Text(required=True, help='Use {placeholder} tokens, e.g. {guest_name}, {room_number}, '
                                            '{date_from}, {date_to}, {amount}.')
    active = fields.Boolean(default=True, string='Enabled')

    # Email is sent alongside the SMS for the same trigger whenever both are
    # filled in. Leave email_subject blank to send SMS only for this trigger.
    email_subject = fields.Char(string='Email Subject')
    email_body = fields.Html(string='Email Body', sanitize=False,
                              help='Same {placeholder} tokens as the SMS body. HTML is allowed.')

    _trigger_property_uniq = models.Constraint(
        'unique(trigger_code, property_id)',
        'Only one template per trigger per property (or global).',
    )

    @api.model
    def _get_template(self, trigger_code, property_id=False):
        domain = [('trigger_code', '=', trigger_code), ('active', '=', True)]
        if property_id:
            tmpl = self.search(domain + [('property_id', '=', property_id)], limit=1)
            if tmpl:
                return tmpl
        return self.search(domain + [('property_id', '=', False)], limit=1)

    @staticmethod
    def _render(body, placeholders):
        def repl(match):
            key = match.group(1)
            return str(placeholders.get(key, '{%s}' % key))
        return re.sub(r'\{(\w+)\}', repl, body or '')

    @api.model
    def send_trigger(self, trigger_code, partner, property_id=False, placeholders=None, related_record=None):
        """Single entry point used by every module in the suite:

            self.env['next.sms.template'].send_trigger(
                'booking_confirmation', reservation.partner_id,
                property_id=reservation.property_id.id,
                placeholders={'guest_name': ..., 'room_number': ..., ...},
                related_record=reservation,
            )

        Resolves the enabled template for (trigger_code, property) and sends
        BOTH channels configured on it, independently of each other:
        - SMS, if `partner.phone` is set and `partner.sms_opt_in` is True -
          queued asynchronously as before, never blocking the caller.
        - Email, if the template has an `email_subject` filled in and
          `partner.email` is set and `partner.email_opt_in` is True - sent
          via Odoo's own outgoing-mail queue (so it never blocks either).
        One channel missing/opted-out/unconfigured never prevents the other.
        Returns the created next.sms.log record (or None if no SMS was sent) -
        existing callers that only check the SMS log are unaffected.
        """
        if not partner:
            return None

        template = self._get_template(trigger_code, property_id=property_id)
        if not template:
            return None

        placeholders = placeholders or {}
        log = None

        if partner.phone and partner.sms_opt_in:
            message = self._render(template.body, placeholders)
            log = self.env['next.sms.log'].create({
                'partner_id': partner.id,
                'property_id': property_id or False,
                'trigger_code': trigger_code,
                'to_number': partner.phone,
                'message': message,
                'status': 'queued',
                'related_model': related_record._name if related_record else False,
                'related_res_id': related_record.id if related_record else False,
            })
            self.env['next.sms.queue']._enqueue(log)

        if template.email_subject and partner.email and partner.email_opt_in:
            subject = self._render(template.email_subject, placeholders)
            body_html = self._render(template.email_body or '', placeholders)
            # Left in the default 'outgoing' state, not .send() here - Odoo's
            # own "Mail: Email Queue Manager" cron delivers it, so (like the
            # SMS path above) this never blocks the caller's transaction.
            self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': body_html,
                'email_to': partner.email,
                'auto_delete': False,
            })

        return log
