# -*- coding: utf-8 -*-
from odoo import models


class NextReservation(models.Model):
    _inherit = 'next.reservation'

    def action_check_out(self):
        res = super().action_check_out()
        HousekeepingTask = self.env['next.housekeeping.task']
        for rec in self:
            for room in rec.room_ids:
                HousekeepingTask.create({
                    'name': 'Post-Checkout Cleaning - %s' % room.name,
                    'room_id': room.id,
                    'task_type': 'checkout_clean',
                })
        return res
