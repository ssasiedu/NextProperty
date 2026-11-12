# -*- coding: utf-8 -*-
"""next_property_id on maintenance.request changed from a plain
related=next_room_id.property_id to a compute that also falls back to the
ticket's equipment's own next_property_id, for tickets against property-
wide equipment (generator, pool pump, lobby AC...) that have no
next_room_id at all - those previously had no property link whatsoever and
were invisible to every property-scoped report/dashboard.

The column already exists (it was a stored related field before), so Odoo
won't recompute it on its own just because the Python behind it changed -
back-fill directly via SQL for the rows this actually affects: no room,
an equipment set, and no property link yet."""


def migrate(cr, version):
    cr.execute("""
        UPDATE maintenance_request mr
        SET next_property_id = me.next_property_id
        FROM maintenance_equipment me
        WHERE mr.equipment_id = me.id
          AND mr.next_room_id IS NULL
          AND mr.next_property_id IS NULL
          AND me.next_property_id IS NOT NULL
    """)
