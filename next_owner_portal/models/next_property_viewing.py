# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextPropertyViewing(models.Model):
    """Slot-based viewing request, integrated with Odoo Calendar so staff see
    it on their normal calendar alongside everything else."""
    _name = 'next.property.viewing'
    _description = 'Property Viewing Request'
    _inherit = ['mail.thread']
    _order = 'date_start desc'

    name = fields.Char(default='Property Viewing', required=True)
    property_id = fields.Many2one('next.property', required=True)
    room_id = fields.Many2one('next.room', help='Optional - specific room/unit to view.')
    owner_id = fields.Many2one('res.partner', string='Requested By (Owner)', required=True,
                                domain=[('is_property_owner', '=', True)])

    purpose = fields.Selection([
        ('routine_inspection', 'Routine Inspection'),
        ('investment_review', 'Investment Review'),
        ('handover', 'Handover'),
    ], required=True, default='routine_inspection')
    notes = fields.Text()

    date_start = fields.Datetime(string='Slot Start', required=True)
    date_end = fields.Datetime(string='Slot End', required=True)

    state = fields.Selection([
        ('requested', 'Requested'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='requested', required=True, tracking=True, copy=False)

    assigned_manager_id = fields.Many2one('res.users', string='Hotel Manager/Staff')
    requires_room_block = fields.Boolean(
        string='Blocks Room for Guest Bookings', default=False,
        help='If set and this viewing requires physical access, the room is set to '
             'grey_blocked for the slot duration once confirmed.')

    calendar_event_id = fields.Many2one('calendar.event', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        Template = self.env['next.sms.template']
        for rec in records:
            if rec.assigned_manager_id:
                Template.send_trigger('owner_viewing_requested', rec.assigned_manager_id.partner_id,
                                       property_id=rec.property_id.id,
                                       placeholders={'property_name': rec.property_id.name,
                                                      'date_from': rec.date_start}, related_record=rec)
        return records

    def action_confirm(self):
        for rec in self:
            event = self.env['calendar.event'].create({
                'name': rec.name,
                'start': rec.date_start,
                'stop': rec.date_end,
                'partner_ids': [(4, rec.owner_id.id), (4, rec.assigned_manager_id.partner_id.id)]
                if rec.assigned_manager_id else [(4, rec.owner_id.id)],
            })
            rec.write({'state': 'confirmed', 'calendar_event_id': event.id})
            if rec.requires_room_block and rec.room_id:
                rec.room_id.action_set_blocked(reason='Owner viewing: %s' % rec.name)
            self.env['next.sms.template'].send_trigger(
                'owner_viewing_confirmed', rec.owner_id, property_id=rec.property_id.id,
                placeholders={'property_name': rec.property_id.name, 'date_from': rec.date_start},
                related_record=rec)

    def action_complete(self):
        for rec in self:
            rec.write({'state': 'completed'})
            if rec.requires_room_block and rec.room_id and rec.room_id.status == 'grey_blocked':
                rec.room_id.action_clear_block()

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancelled'})
            if rec.calendar_event_id:
                rec.calendar_event_id.unlink()
            if rec.requires_room_block and rec.room_id and rec.room_id.status == 'grey_blocked':
                rec.room_id.action_clear_block()
