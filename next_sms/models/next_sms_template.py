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
    ('equipment_maintenance_due_soon', 'Maintenance: Equipment Preventive Maintenance Due Soon'),
    ('equipment_maintenance_overdue', 'Maintenance: Equipment Preventive Maintenance Overdue'),
    ('equipment_maintenance_completed', 'Maintenance: Equipment Preventive Maintenance Completed'),
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

    def _build_email_html(self, subject, body_html, property_id=False):
        """Wraps a template's (plain) email_body in a consistent, branded
        shell - banner, card, footer - applied at send time rather than
        baked into each of the 20 seed templates' stored HTML. That means:
        one place to keep the look consistent, it applies to every trigger
        immediately (no noupdate="1" migration needed to reach an existing
        database - see next_sms/migrations/19.0.1.1.0 for why that matters
        here), and it never clobbers an admin's own edits to a template's
        *content*, since only the wrapper around it is templated code.
        Table-based layout with inline styles throughout - the only markup
        Outlook's rendering engine reliably honours in an email."""
        company = self.env.company
        brand_name = company.name or 'NEXT Property Management'
        if property_id:
            property_name = self.env['next.property'].browse(property_id).name
            if property_name:
                brand_name = property_name

        logo_html = ''
        if company.logo:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
            logo_url = '%s/web/image/res.company/%s/logo' % (base_url, company.id)
            logo_html = (
                '<img src="%s" alt="%s" height="40" '
                'style="height:40px;max-height:40px;width:auto;display:block;margin:0 auto 10px;"/>'
            ) % (logo_url, brand_name)

        return '''<table role="presentation" width="100%%" cellpadding="0" cellspacing="0"
       style="background-color:#F3F4F6;padding:32px 16px;font-family:Arial,Helvetica,sans-serif;">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%%;background-color:#FFFFFF;border-radius:8px;overflow:hidden;">
      <tr>
        <td align="center" style="background-color:#0F3D3E;padding:28px 24px;">
          %(logo_html)s
          <div style="color:#FFFFFF;font-size:20px;font-weight:bold;letter-spacing:0.3px;">%(brand_name)s</div>
        </td>
      </tr>
      <tr>
        <td style="padding:32px 28px;color:#1F2937;font-size:15px;line-height:1.6;">
          %(body_html)s
        </td>
      </tr>
      <tr>
        <td style="background-color:#F9FAFB;padding:18px 28px;border-top:1px solid #E5E7EB;
                   color:#9CA3AF;font-size:12px;line-height:1.5;text-align:center;">
          This is an automated message from %(brand_name)s. Please do not reply directly to this email.
        </td>
      </tr>
    </table>
  </td></tr>
</table>''' % {'logo_html': logo_html, 'brand_name': brand_name, 'body_html': body_html}

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
            # Wrap every trigger's raw content in the shared branded banner/
            # card/footer shell - see _build_email_html's docstring for why
            # this happens here rather than in each template's stored HTML.
            full_html = self._build_email_html(subject, body_html, property_id=property_id)
            # Left in the default 'outgoing' state, not .send() here - Odoo's
            # own "Mail: Email Queue Manager" cron delivers it, so (like the
            # SMS path above) this never blocks the caller's transaction.
            self.env['mail.mail'].sudo().create({
                'subject': subject,
                'body_html': full_html,
                'email_to': partner.email,
                'auto_delete': False,
            })

        return log
