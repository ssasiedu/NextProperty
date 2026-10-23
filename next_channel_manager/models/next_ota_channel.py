# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NextOtaChannel(models.Model):
    """Configuration for one connected OTA. `_get_adapter()` resolves the
    Python adapter class (see ota_adapters.py) that actually talks to that
    OTA's API - adding a new OTA means registering a new adapter key, not
    changing this model or the sync logic below."""
    _name = 'next.ota.channel'
    _description = 'OTA Channel'

    name = fields.Char(required=True)
    channel_type = fields.Selection([
        ('airbnb', 'Airbnb'),
        ('expedia', 'Expedia'),
        ('booking_com', 'Booking.com'),
    ], required=True)
    property_id = fields.Many2one('next.property', required=True)
    active = fields.Boolean(default=True)

    api_key = fields.Char()
    api_secret = fields.Char()
    external_listing_id = fields.Char(help='The OTA-side listing/property id this maps to.')

    sync_rates = fields.Boolean(default=True)
    sync_availability = fields.Boolean(default=True)
    last_sync_date = fields.Datetime(readonly=True)
    last_sync_status = fields.Char(readonly=True)

    def _get_adapter(self):
        from .ota_adapters import get_adapter_class
        self.ensure_one()
        adapter_cls = get_adapter_class(self.channel_type)
        return adapter_cls(self)

    def action_sync_now(self):
        for channel in self:
            adapter = channel._get_adapter()
            try:
                if channel.sync_availability:
                    adapter.push_availability(channel._collect_availability_payload())
                if channel.sync_rates:
                    adapter.push_rates(channel._collect_rates_payload())
                channel.write({'last_sync_date': fields.Datetime.now(), 'last_sync_status': 'ok'})
            except Exception as exc:  # noqa: broad-except - a sync failure must never crash the cron
                channel.write({'last_sync_date': fields.Datetime.now(), 'last_sync_status': 'error: %s' % exc})

    def _collect_availability_payload(self):
        self.ensure_one()
        Ledger = self.env['next.availability.ledger']
        rows = Ledger.search([
            ('room_id.property_id', '=', self.property_id.id),
            ('date', '>=', fields.Date.today()),
        ])
        by_room = {}
        for row in rows:
            by_room.setdefault(row.room_id.id, []).append({
                'date': row.date.isoformat(),
                'available': not (row.reservation_id or row.ota_hold_channel),
            })
        return by_room

    def _collect_rates_payload(self):
        self.ensure_one()
        return {
            rt.id: {'name': rt.name, 'rate': rt.list_price, 'weekend_rate': rt.weekend_price or rt.list_price}
            for rt in self.property_id.room_type_ids
        }

    def process_incoming_booking(self, external_payload):
        """Called by the OTA webhook controller (or a polling adapter) when
        a booking is made on the OTA side. Resolves rooms/dates from the
        payload and goes through the SAME availability-ledger locking as
        every other channel, so an OTA booking can never create a double
        booking against the website or a walk-in."""
        self.ensure_one()
        room = self.env['next.room'].search([
            ('property_id', '=', self.property_id.id),
            ('room_type_id.name', '=', external_payload.get('room_type_name')),
        ], limit=1)
        if not room:
            return False

        date_from = fields.Date.from_string(external_payload['date_from'])
        date_to = fields.Date.from_string(external_payload['date_to'])

        reservation = self.env['next.reservation'].create({
            'property_id': self.property_id.id,
            'partner_id': self.env['res.partner']._find_or_create_ota_guest(external_payload),
            'date_from': date_from,
            'date_to': date_to,
            'adults': external_payload.get('adults', 1),
            'children': external_payload.get('children', 0),
            'room_ids': [(6, 0, [room.id])],
            'booking_source': 'ota',
            'ota_channel': self.channel_type,
            'ota_reference': external_payload.get('external_reference'),
        })
        reservation.action_confirm()
        self.env['next.sms.template'].send_trigger(
            'channel_ota_booking_received', self.property_id.manager_id.partner_id or self.env.user.partner_id,
            property_id=self.property_id.id,
            placeholders={'channel': self.channel_type, 'property_name': self.property_id.name,
                          'date_from': date_from, 'date_to': date_to},
            related_record=reservation)
        return reservation
