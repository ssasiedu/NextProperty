# -*- coding: utf-8 -*-
from odoo import models


class NextHousekeepingTask(models.Model):
    _inherit = 'next.housekeeping.task'

    def action_complete(self):
        res = super().action_complete()
        Template = self.env['next.sms.template']
        front_desk_group = self.env.ref('next_base.group_next_front_desk')
        for rec in self:
            for staff in self.env['res.users'].search([('groups_id', 'in', front_desk_group.id)]).mapped('partner_id'):
                Template.send_trigger('housekeeping_room_ready', staff,
                                       property_id=rec.property_id.id,
                                       placeholders={'room_number': rec.room_id.name}, related_record=rec)
        return res

    def _cron_flag_overdue_tasks(self):
        res = super()._cron_flag_overdue_tasks()
        Template = self.env['next.sms.template']
        from odoo import fields
        overdue = self.search([('deadline', '<', fields.Datetime.now()), ('state', '!=', 'complete')])
        for task in overdue:
            recipient = task.supervisor_id.partner_id if task.supervisor_id else False
            if recipient:
                Template.send_trigger('housekeeping_task_overdue', recipient,
                                       property_id=task.property_id.id,
                                       placeholders={'room_number': task.room_id.name, 'guest_name': ''},
                                       related_record=task)
        return res
