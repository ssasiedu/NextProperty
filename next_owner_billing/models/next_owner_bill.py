# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class NextOwnerBill(models.Model):
    """One monthly service-charge invoice against an owner (team review
    item #11) - either raised automatically from a next.owner.service.charge
    or created standalone for a one-off charge. Payment is tracked via a
    ledger of next.owner.bill.payment lines (supports partial payment),
    mirroring next.owner.net.revenue's paid/confirmed workflow but in the
    other direction: here the OWNER owes the business, so the owner
    self-reports a payment from their portal and Accountant/Manager
    confirms it - only a confirmed payment reduces the owner's balance."""
    _name = 'next.owner.bill'
    _description = 'Owner Service Charge Bill'
    _inherit = ['mail.thread']
    _order = 'period_year desc, period_month desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    owner_id = fields.Many2one('res.partner', string='Owner', required=True, tracking=True)
    property_id = fields.Many2one('next.property', string='Property', required=True, tracking=True)
    service_charge_id = fields.Many2one(
        'next.owner.service.charge', string='Recurring Charge', readonly=True,
        help='Blank for a one-off bill created directly rather than by the monthly cron.')

    period_month = fields.Selection([(str(i), str(i)) for i in range(1, 13)], required=True)
    period_year = fields.Char(required=True, default=lambda self: str(fields.Date.today().year))

    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                   default=lambda self: self.env.company.currency_id)
    invoice_date = fields.Date(default=fields.Date.context_today, required=True)
    due_date = fields.Date(required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)

    payment_ids = fields.One2many('next.owner.bill.payment', 'bill_id', string='Payments')
    amount_paid = fields.Monetary(compute='_compute_amounts', store=True)
    balance = fields.Monetary(compute='_compute_amounts', store=True)
    payment_state = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
    ], compute='_compute_amounts', store=True, tracking=True)
    has_pending_report = fields.Boolean(
        compute='_compute_amounts', store=True,
        help='A payment the owner self-reported is awaiting Accountant/Manager confirmation.')

    # Plain stored field, not a compute depending on due_date/today - "today"
    # passing is not a dependency Odoo can react to on its own (the same
    # reason maintenance.equipment.preventive_overdue is a plain field the
    # daily cron flips, not a compute keyed off next_maintenance_date).
    # _cron_send_defaulter_reminders below is what keeps this current, once
    # a day; _compute_amounts clears it the moment a bill is paid in full.
    is_defaulter = fields.Boolean(
        default=False, readonly=True, copy=False,
        help='Past due date, issued, and not yet fully confirmed paid - refreshed daily.')
    reminder_count = fields.Integer(default=0, readonly=True, copy=False)
    last_reminder_date = fields.Date(readonly=True, copy=False)

    _service_charge_period_uniq = models.Constraint(
        'unique(service_charge_id, period_month, period_year)',
        'A bill for this recurring charge and period already exists.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('next.owner.bill') or 'New'
        return super().create(vals_list)

    @api.depends('payment_ids.amount', 'payment_ids.state', 'amount')
    def _compute_amounts(self):
        for rec in self:
            confirmed = rec.payment_ids.filtered(lambda p: p.state == 'confirmed')
            rec.amount_paid = sum(confirmed.mapped('amount'))
            rec.balance = rec.amount - rec.amount_paid
            rec.has_pending_report = bool(rec.payment_ids.filtered(lambda p: p.state == 'reported'))
            if rec.balance <= 0.004:
                rec.payment_state = 'paid'
                if rec.is_defaulter:
                    rec.is_defaulter = False  # Cleared the moment it's paid in full - don't wait for the cron.
            elif rec.amount_paid > 0:
                rec.payment_state = 'partially_paid'
            else:
                rec.payment_state = 'unpaid'

    def action_issue(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            rec.write({'state': 'issued'})
            self.env['next.sms.template'].send_trigger(
                'owner_billing_invoice_raised', rec.owner_id, property_id=rec.property_id.id,
                placeholders={
                    'property_name': rec.property_id.name, 'amount': rec.amount,
                    'period': '%s/%s' % (rec.period_month, rec.period_year),
                    'due_date': rec.due_date,
                }, related_record=rec)
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_report_payment(self, amount, reference=None, payment_date=None):
        """Called by the owner from the portal (owner_billing_portal.py),
        which is responsible for checking the bill actually belongs to them
        first. Does NOT reduce the balance by itself - see
        next.owner.bill.payment for why."""
        self.ensure_one()
        if self.state != 'issued':
            raise UserError('This bill is not open for payment.')
        payment = self.env['next.owner.bill.payment'].sudo().create({
            'bill_id': self.id, 'amount': amount, 'reference': reference,
            'payment_date': payment_date or fields.Date.context_today(self),
            'state': 'reported',
        })
        Template = self.env['next.sms.template']
        for recipient in self._get_management_recipients():
            Template.send_trigger(
                'owner_billing_payment_reported', recipient, property_id=self.property_id.id,
                placeholders={'owner_name': self.owner_id.name, 'property_name': self.property_id.name,
                              'amount': amount, 'bill_name': self.name}, related_record=self)
        return payment

    def _get_management_recipients(self):
        users = self.env['res.users'].search([
            ('group_ids', 'in', (self.env.ref('next_base.group_next_accountant')
                                  | self.env.ref('next_base.group_next_manager')).ids)])
        return users.mapped('partner_id')

    def _cron_send_defaulter_reminders(self):
        """Daily: "A defaulters message should automatically be sent as
        well as reminders." Searches on due_date/state/payment_state
        directly - not the stored is_defaulter flag, which "today" moving
        forward can't refresh by itself - flips is_defaulter on for
        anything newly overdue, then sends every currently-overdue,
        unpaid/partially-paid bill a reminder SMS (bumping reminder_count) -
        at most one per day per bill, since this cron itself runs daily."""
        today = fields.Date.context_today(self)
        defaulters = self.search([
            ('state', '=', 'issued'), ('payment_state', '!=', 'paid'), ('due_date', '<', today)])
        defaulters.filtered(lambda b: not b.is_defaulter).write({'is_defaulter': True})
        for bill in defaulters:
            bill.write({
                'reminder_count': bill.reminder_count + 1,
                'last_reminder_date': fields.Date.context_today(self),
            })
            self.env['next.sms.template'].send_trigger(
                'owner_billing_defaulter_reminder', bill.owner_id, property_id=bill.property_id.id,
                placeholders={
                    'property_name': bill.property_id.name, 'balance': bill.balance,
                    'period': '%s/%s' % (bill.period_month, bill.period_year), 'due_date': bill.due_date,
                }, related_record=bill)


class NextOwnerBillPayment(models.Model):
    """One payment event against a bill - owner-self-reported ('reported',
    awaiting confirmation) or entered/confirmed directly by Accountant/
    Manager. Only a 'confirmed' line counts toward amount_paid/balance on
    the parent bill (see next.owner.bill._compute_amounts) - "when the
    owner pays the system should reduce the owner's balance" is read here
    as "once that payment is verified received", the same trust boundary
    next.owner.net.revenue's payment_state already uses in the other
    direction."""
    _name = 'next.owner.bill.payment'
    _description = 'Owner Bill Payment'
    _order = 'payment_date desc, id desc'

    bill_id = fields.Many2one('next.owner.bill', required=True, ondelete='cascade')
    owner_id = fields.Many2one(related='bill_id.owner_id', store=True)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related='bill_id.currency_id', store=True)
    payment_date = fields.Date(default=fields.Date.context_today, required=True)
    reference = fields.Char(help='Bank transfer reference, mobile money transaction id, etc.')

    state = fields.Selection([
        ('reported', 'Reported - Awaiting Confirmation'),
        ('confirmed', 'Confirmed'),
    ], default='reported', required=True, copy=False)
    confirmed_by = fields.Many2one('res.users', readonly=True, copy=False)
    confirmed_date = fields.Datetime(readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        # Accountant/Manager entering a payment themselves (they've already
        # verified it hit the bank/mobile money) is confirming it on the
        # spot - only the owner's own self-report (created via sudo() from
        # the portal controller, an uid without this group) waits for review.
        is_staff = self.env.user.has_group('next_base.group_next_accountant') \
            or self.env.user.has_group('next_base.group_next_manager')
        for vals in vals_list:
            if is_staff and vals.get('state', 'reported') == 'reported':
                vals.update({'state': 'confirmed', 'confirmed_by': self.env.user.id,
                             'confirmed_date': fields.Datetime.now()})
        records = super().create(vals_list)
        for rec in records:
            if rec.state == 'confirmed':
                rec._notify_confirmed()
        return records

    def action_confirm(self):
        for rec in self:
            if rec.state == 'confirmed':
                continue
            rec.write({'state': 'confirmed', 'confirmed_by': self.env.user.id,
                       'confirmed_date': fields.Datetime.now()})
            rec._notify_confirmed()

    def _notify_confirmed(self):
        for rec in self:
            rec.bill_id.message_post(body='Payment of %s confirmed (ref: %s).' % (
                rec.amount, rec.reference or 'none'))
            self.env['next.sms.template'].send_trigger(
                'owner_billing_payment_confirmed', rec.owner_id, property_id=rec.bill_id.property_id.id,
                placeholders={
                    'property_name': rec.bill_id.property_id.name, 'amount': rec.amount,
                    'balance': rec.bill_id.balance, 'bill_name': rec.bill_id.name,
                }, related_record=rec.bill_id)
