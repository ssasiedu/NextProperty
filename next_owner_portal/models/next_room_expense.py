# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextRoomExpense(models.Model):
    """Internal expense entries (utilities, repairs, supplies, commissions,
    overhead) linked to a room/property, period-based. Feeds the internal
    net-income calculation that management reconciles against the manual
    `next.owner.net.revenue` figure BEFORE anything publishes to the owner.
    This model and its computed net-income are never shown on the Owner
    Portal directly."""
    _name = 'next.room.expense'
    _description = 'Room/Property Expense'
    _order = 'period_year desc, period_month desc'

    property_id = fields.Many2one('next.property', required=True)
    room_id = fields.Many2one('next.room', help='Leave empty for a property-level expense.')

    category = fields.Selection([
        ('utilities', 'Utilities'),
        ('repairs', 'Repairs'),
        ('supplies', 'Supplies'),
        ('commissions', 'Commissions'),
        ('overhead', 'Overhead'),
        ('other', 'Other'),
    ], required=True, default='other')

    period_month = fields.Selection([(str(i), str(i)) for i in range(1, 13)], required=True)
    # Char, not Integer - see next_owner_net_revenue.py for why (avoids the
    # "2,026" thousands-separator bug on a plain year label).
    period_year = fields.Char(required=True, default=lambda self: str(fields.Date.today().year))

    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                   default=lambda self: self.env.company.currency_id)
    description = fields.Char()


class NextRoomNetIncome(models.Model):
    """Internal, management-facing computation: room_revenue minus allocated
    expenses for a configurable period. This is NOT the figure shown to
    owners - see next.owner.net.revenue for that. Used to reconcile before
    a settlement statement publishes (section 8.3 of the spec)."""
    _inherit = 'next.room'

    def compute_internal_net_income(self, period_month, period_year):
        self.ensure_one()
        Folio = self.env['next.folio']
        folios = Folio.search([
            ('reservation_id.room_ids', 'in', self.id),
            ('state', 'in', ('finalized', 'invoiced')),
        ])
        revenue = 0.0
        for folio in folios:
            checkout = folio.reservation_id.actual_checkout
            if checkout and str(checkout.month) == str(period_month) and str(checkout.year) == str(period_year):
                revenue += folio.amount_total

        expenses = self.env['next.room.expense'].search([
            ('room_id', '=', self.id), ('period_month', '=', str(period_month)),
            ('period_year', '=', str(period_year)),
        ])
        total_expenses = sum(expenses.mapped('amount'))
        return {
            'room_revenue': revenue,
            'allocated_expenses': total_expenses,
            'net_income': revenue - total_expenses,
        }

    def action_generate_settlement_statement(self, period_month, period_year):
        """Reconciles the internal net_income against the published
        next.owner.net.revenue figure for the same period, then generates
        the Owner Settlement/Payout Statement PDF (report/*). Raises a
        warning (posted as a message, not a hard stop) if they diverge
        significantly, so management can review before sending to the owner."""
        NetRevenue = self.env['next.owner.net.revenue']
        for room in self:
            internal = room.compute_internal_net_income(period_month, period_year)
            published = NetRevenue.search([
                ('room_id', '=', room.id), ('period_month', '=', str(period_month)),
                ('period_year', '=', str(period_year)), ('state', '=', 'published'),
            ], limit=1)
            if published and abs(published.amount - internal['net_income']) > 0.01:
                room.message_post(
                    body='Reconciliation warning: published net revenue (%.2f) differs from internally '
                         'computed net income (%.2f) for %s/%s.' % (
                             published.amount, internal['net_income'], period_month, period_year))
        return self.env.ref('next_owner_portal.action_report_next_owner_settlement').report_action(self)
