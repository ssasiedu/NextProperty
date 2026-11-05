# -*- coding: utf-8 -*-
from odoo import fields, models


class NextReservation(models.Model):
    """Team review item #8: the customer portal needs a place to leave
    feedback about their stay. Rather than build a parallel feedback model,
    this issues one `survey.user_input` (native `survey` app) per stay
    against the seeded 'Guest Stay Feedback' survey (next_guest_survey_data.xml)
    at checkout - the survey's own public, token-based fill-in page (no
    login required, exactly what a one-off public/anonymous guest needs)
    is the actual feedback form; this module only wires up when it's
    issued and where the guest finds the link."""
    _inherit = 'next.reservation'

    survey_user_input_id = fields.Many2one(
        'survey.user_input', string='Feedback Survey', readonly=True, copy=False,
        help='The feedback-survey answer issued to this guest at checkout, if any.')
    survey_feedback_url = fields.Char(compute='_compute_survey_feedback_url', string='Feedback Link')

    def _compute_survey_feedback_url(self):
        for rec in self:
            answer = rec.survey_user_input_id
            rec.survey_feedback_url = (
                '%s?answer_token=%s' % (answer.survey_id.get_start_url(), answer.access_token)
            ) if answer else False

    def action_check_out(self):
        res = super().action_check_out()
        for rec in self:
            rec._next_issue_feedback_survey()
        return res

    def _next_issue_feedback_survey(self):
        """Default: chatter note + email with the link, so this works even
        without next_sms installed (same "extend, don't require" pattern as
        maintenance.equipment's _notify_* hooks) - next_sms adds an SMS
        invite too, via its own override of this method."""
        self.ensure_one()
        if self.survey_user_input_id:
            return  # Checkout only ever issues one invite per stay.
        survey = self.env.ref('next_booking.survey_next_guest_feedback', raise_if_not_found=False)
        if not survey or not self.partner_id:
            return
        answer = survey.sudo()._create_answer(
            partner=self.partner_id.sudo(), email=self.partner_id.email, check_attempts=False)
        self.survey_user_input_id = answer.id
        url = self.survey_feedback_url
        self.message_post(body='Feedback survey sent to the guest: <a href="%s">%s</a>' % (url, url))
        if self.partner_id.email:
            self.env['mail.mail'].sudo().create({
                'subject': 'How was your stay at %s?' % self.property_id.name,
                'body_html': '<p>Hi %s,</p><p>Thank you for staying with us at %s. '
                              'We would love to hear how it went - it only takes a minute:</p>'
                              '<p><a href="%s">Share your feedback</a></p>' % (
                                  self.partner_id.name, self.property_id.name, url),
                'email_to': self.partner_id.email,
                'auto_delete': False,
            })
