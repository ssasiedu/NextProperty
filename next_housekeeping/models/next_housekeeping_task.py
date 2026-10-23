# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextHousekeepingTask(models.Model):
    _name = 'next.housekeeping.task'
    _description = 'Housekeeping Task'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(required=True, default='Room Servicing')
    room_id = fields.Many2one('next.room', required=True, tracking=True)
    property_id = fields.Many2one(related='room_id.property_id', store=True)

    task_type = fields.Selection([
        ('checkout_clean', 'Post-Checkout Cleaning'),
        ('routine', 'Routine Servicing'),
        ('deep_clean', 'Deep Clean'),
    ], default='checkout_clean', required=True)

    state = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('inspected', 'Inspected'),
        ('complete', 'Complete'),
    ], default='not_started', required=True, tracking=True, copy=False)

    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True,
                                   domain=lambda self: [('groups_id', 'in',
                                                          self.env.ref('next_base.group_next_housekeeping').id)])
    supervisor_id = fields.Many2one('res.users', string='Supervisor')

    deadline = fields.Datetime()
    started_date = fields.Datetime(readonly=True, copy=False)
    completed_date = fields.Datetime(readonly=True, copy=False)
    is_overdue = fields.Boolean(compute='_compute_is_overdue')

    notes = fields.Text()

    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.deadline and rec.deadline < now and rec.state != 'complete')

    def action_start(self):
        self.write({'state': 'in_progress', 'started_date': fields.Datetime.now()})

    def action_mark_inspected(self):
        self.write({'state': 'inspected'})

    def action_complete(self):
        for rec in self:
            rec.write({'state': 'complete', 'completed_date': fields.Datetime.now()})
            if rec.room_id.status == 'red_pending_checkout':
                rec.room_id.write({'status': 'green_ready'})
                # next_sms: 'Room flipped to green/ready' trigger fires to Front Desk here.

    @api.model
    def _cron_create_routine_tasks(self):
        """Daily cron: create a routine-servicing task for every currently
        occupied room that doesn't already have an open task today."""
        occupied_rooms = self.env['next.room'].search([('status', '=', 'yellow_occupied')])
        for room in occupied_rooms:
            existing = self.search([
                ('room_id', '=', room.id), ('task_type', '=', 'routine'),
                ('state', 'not in', ('complete',)),
                ('create_date', '>=', fields.Datetime.to_string(fields.Date.today())),
            ])
            if not existing:
                self.create({
                    'name': 'Routine Servicing - %s' % room.name,
                    'room_id': room.id,
                    'task_type': 'routine',
                })

    @api.model
    def _cron_flag_overdue_tasks(self):
        """Daily/hourly cron companion: notifies supervisors of overdue tasks.
        Actual SMS/notification dispatch is delegated to next_sms's
        'Task overdue -> Supervisor' trigger; this just ensures is_overdue
        is accurate and posts an activity/message for visibility."""
        overdue = self.search([('deadline', '<', fields.Datetime.now()), ('state', '!=', 'complete')])
        for task in overdue:
            task.message_post(body='Housekeeping task "%s" is overdue.' % task.name)
