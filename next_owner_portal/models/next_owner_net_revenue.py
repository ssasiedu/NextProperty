# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class NextOwnerNetRevenue(models.Model):
    """The ONLY net-revenue figure ever displayed to a Property Owner.
    Manually entered and reviewed by Accountant/Manager; never derived from
    `next.room.expense` / system-computed net income (next_bi_report /
    next_room.net_income are internal-only and reconciled against this
    figure before anything is published, per spec section 8.3).

    Once published, the record is locked: further corrections must go
    through a new revision record (action_create_revision), never a silent
    edit of a published figure - this is the audit trail."""
    _name = 'next.owner.net.revenue'
    _description = 'Owner Net Revenue Statement'
    _inherit = ['mail.thread']
    _order = 'period_year desc, period_month desc'

    property_id = fields.Many2one('next.property', required=True)
    room_id = fields.Many2one('next.room', help='Leave empty for a property-level statement.')

    period_month = fields.Selection([(str(i), str(i)) for i in range(1, 13)], required=True)
    period_year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)

    amount = fields.Monetary(required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                   default=lambda self: self.env.company.currency_id)

    entered_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    date_entered = fields.Datetime(default=fields.Datetime.now, readonly=True)
    notes = fields.Text()
    attachment = fields.Binary(string='Supporting Document')
    attachment_filename = fields.Char()

    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('superseded', 'Superseded'),
    ], default='draft', required=True, tracking=True, copy=False)

    supersedes_id = fields.Many2one('next.owner.net.revenue', string='Supersedes', readonly=True, copy=False)
    revision_number = fields.Integer(default=1, readonly=True)

    _period_property_room_uniq = models.Constraint(
        'unique(property_id, room_id, period_month, period_year, state)',
        'Use a revision instead of a duplicate entry for the same property/room/period '
        '(the unique constraint includes state so a superseded row can coexist with its replacement).',
    )

    def action_publish(self):
        """Requires Accountant/Manager (enforced by record rule + group access,
        not just this check) and locks the record."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError('Only draft statements can be published.')
            rec.write({'state': 'published'})
            Template = self.env['next.sms.template']
            for owner in rec.property_id.owner_ids:
                Template.send_trigger('owner_net_revenue_published', owner,
                                       property_id=rec.property_id.id,
                                       placeholders={
                                           'property_name': rec.property_id.name,
                                           'period': '%s/%s' % (rec.period_month, rec.period_year),
                                           'amount': rec.amount,
                                       }, related_record=rec)

    def action_create_revision(self):
        """The only way to change a published figure: create a new draft
        copy linked back via supersedes_id, requiring supervisor review/
        re-publish. The original stays untouched and moves to 'superseded'
        only once the revision itself is published - so there is never a
        gap where neither record is published, and never a silent edit."""
        self.ensure_one()
        if self.state != 'published':
            raise UserError('Only published statements can be revised. Edit drafts directly instead.')
        revision = self.copy({
            'state': 'draft',
            'supersedes_id': self.id,
            'revision_number': self.revision_number + 1,
            'entered_by': self.env.user.id,
            'date_entered': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Revise Net Revenue Statement',
            'res_model': 'next.owner.net.revenue',
            'view_mode': 'form',
            'res_id': revision.id,
            'target': 'current',
        }

    def write(self, vals):
        for rec in self:
            if rec.state == 'published' and not self.env.context.get('next_allow_published_write'):
                protected = {'amount', 'period_month', 'period_year', 'property_id', 'room_id'}
                if protected & set(vals.keys()):
                    raise UserError(
                        'This statement is published and locked. Use "Create Revision" to correct it.')
        return super().write(vals)

    def _publish_revision_chain(self):
        """Called when a revision is published: flips the superseded original."""
        for rec in self:
            if rec.supersedes_id and rec.state == 'published':
                rec.supersedes_id.with_context(next_allow_published_write=True).write({'state': 'superseded'})

    def action_publish_revision(self):
        self.action_publish()
        self._publish_revision_chain()
