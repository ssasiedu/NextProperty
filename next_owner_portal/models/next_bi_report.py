# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class NextBiReservationReport(models.Model):
    """Internal/management-facing BI dashboard source. A SQL view (not a
    regular table) over next.reservation/next.folio for fast KPI queries:
    gross revenue trend, occupancy rate, booking-source split, cancellation
    stats, ADR (Average Daily Rate) and RevPAR (Revenue per Available Room).
    System-computed net revenue is deliberately NOT included here in any
    owner-facing form - see next.owner.net.revenue for what owners see."""
    _name = 'next.bi.reservation.report'
    _description = 'Reservation BI Report (Internal)'
    _auto = False
    _order = 'date_from desc'

    reservation_id = fields.Many2one('next.reservation', readonly=True)
    property_id = fields.Many2one('next.property', readonly=True)
    date_from = fields.Date(readonly=True)
    nights = fields.Integer(readonly=True)
    booking_source = fields.Selection([('direct', 'Direct'), ('walk_in', 'Walk-in'), ('ota', 'OTA')], readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'), ('cancelled', 'Cancelled'),
    ], readonly=True)
    room_count = fields.Integer(readonly=True)
    gross_revenue = fields.Monetary(readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    r.id AS id,
                    r.id AS reservation_id,
                    r.property_id AS property_id,
                    r.date_from::date AS date_from,
                    r.nights AS nights,
                    r.booking_source AS booking_source,
                    r.state AS state,
                    (SELECT count(*) FROM next_reservation_room_rel rr WHERE rr.reservation_id = r.id) AS room_count,
                    COALESCE(f.amount_total, 0) AS gross_revenue,
                    p.currency_id AS currency_id
                FROM next_reservation r
                JOIN next_property p ON p.id = r.property_id
                LEFT JOIN next_folio f ON f.id = r.folio_id
            )
        """ % self._table)

    @api.model
    def get_kpis(self, property_id=False, date_from=False, date_to=False):
        """Returns the KPI dict consumed by the BI dashboard client action:
        gross revenue trend, occupancy rate, booking-source split,
        cancellation stats, ADR, RevPAR."""
        domain = []
        if property_id:
            domain.append(('property_id', '=', property_id))
        if date_from:
            domain.append(('date_from', '>=', date_from))
        if date_to:
            domain.append(('date_from', '<=', date_to))

        records = self.search(domain)
        booked = records.filtered(lambda r: r.state != 'cancelled')
        cancelled = records.filtered(lambda r: r.state == 'cancelled')

        total_room_nights = sum(booked.mapped(lambda r: r.room_count * r.nights))
        gross_revenue = sum(booked.mapped('gross_revenue'))

        Room = self.env['next.room']
        room_domain = [('property_id', '=', property_id)] if property_id else []
        available_rooms = Room.search_count(room_domain) or 1
        days_in_range = max((fields.Date.from_string(date_to) - fields.Date.from_string(date_from)).days, 1) \
            if date_from and date_to else 30
        available_room_nights = available_rooms * days_in_range

        adr = (gross_revenue / total_room_nights) if total_room_nights else 0.0
        revpar = (gross_revenue / available_room_nights) if available_room_nights else 0.0
        occupancy_rate = (total_room_nights / available_room_nights * 100) if available_room_nights else 0.0

        source_split = {}
        for source in ('direct', 'walk_in', 'ota'):
            source_split[source] = len(booked.filtered(lambda r: r.booking_source == source))

        return {
            'gross_revenue': gross_revenue,
            'occupancy_rate': round(occupancy_rate, 2),
            'adr': round(adr, 2),
            'revpar': round(revpar, 2),
            'booking_source_split': source_split,
            'cancellation_count': len(cancelled),
            'cancellation_rate': round(len(cancelled) / len(records) * 100, 2) if records else 0.0,
        }
