# -*- coding: utf-8 -*-
from odoo import fields, models


class NextEquipmentCostLine(models.Model):
    """One line per cost event against a piece of equipment: the actual
    spend when a preventive ticket is completed (optionally logged via
    next.maintenance.request's Actual Cost field), a one-off repair, or an
    overdue penalty posted automatically by
    maintenance.equipment._cron_check_preventive_maintenance. Feeds
    maintenance.equipment.total_maintenance_cost and the management
    report/pivot - a simple running ledger of what each piece of equipment
    has actually cost to keep running, separate from its one-time purchase
    `cost` (native field)."""
    _name = 'next.equipment.cost.line'
    _description = 'Equipment Maintenance Cost Line'
    _order = 'date desc, id desc'

    equipment_id = fields.Many2one('maintenance.equipment', required=True, ondelete='cascade')
    next_property_id = fields.Many2one(
        related='equipment_id.next_property_id', store=True, string='Property')
    date = fields.Date(default=fields.Date.context_today, required=True)
    cost_type = fields.Selection([
        ('preventive', 'Preventive Maintenance'),
        ('repair', 'Repair / Corrective'),
        ('overdue_penalty', 'Overdue Penalty'),
        ('other', 'Other'),
    ], default='preventive', required=True)
    amount = fields.Float(required=True)
    description = fields.Char()
    maintenance_request_id = fields.Many2one('maintenance.request', string='Related Ticket')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
