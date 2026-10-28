# -*- coding: utf-8 -*-
"""Reverts the "plain OR" simplification made in 19.0.1.2.0 back to an
EXCLUSIVE fallback (next.room.owner_id, when set, is authoritative;
property-level ownership only applies when owner_id is blank).

19.0.1.2.0 assumed any already-set owner_id was stale leftover test data
and should never be able to narrow access below plain property-level
ownership. Confirmed wrong: Roxy Hotel genuinely has two co-owners
(ROXYMAN, NANA) in next.property.owner_ids, each owning specific rooms
via next.room.owner_id (101/201 -> ROXYMAN, 102/301 -> NANA). With a
plain OR, both of them satisfied the property-level branch regardless of
owner_id, so each could see all four rooms - a real data leak between
co-owners, not a fix. Restoring the exclusive form from 19.0.1.1.0.

As with the previous two migrations, these are noupdate="1" rules that
already exist in every database that ran 19.0.1.2.0, so this corrects
them directly via SQL."""

DOMAINS = {
    'rule_next_room_owner': (
        "['|', ('owner_id.user_ids', 'in', [user.id]),"
        " '&', ('owner_id', '=', False), ('property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_reservation_owner': (
        "['|', ('room_ids.owner_id.user_ids', 'in', [user.id]),"
        " '&', ('room_ids.owner_id', '=', False), ('room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_folio_owner': (
        "['|', ('reservation_id.room_ids.owner_id.user_ids', 'in', [user.id]),"
        " '&', ('reservation_id.room_ids.owner_id', '=', False),"
        " ('reservation_id.room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_folio_line_owner': (
        "['|', ('folio_id.reservation_id.room_ids.owner_id.user_ids', 'in', [user.id]),"
        " '&', ('folio_id.reservation_id.room_ids.owner_id', '=', False),"
        " ('folio_id.reservation_id.room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_folio_payment_owner': (
        "['|', ('folio_id.reservation_id.room_ids.owner_id.user_ids', 'in', [user.id]),"
        " '&', ('folio_id.reservation_id.room_ids.owner_id', '=', False),"
        " ('folio_id.reservation_id.room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
}


def migrate(cr, version):
    for xml_name, domain in DOMAINS.items():
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE module = 'next_base' AND name = %s AND model = 'ir.rule'",
            (xml_name,),
        )
        row = cr.fetchone()
        if not row:
            continue
        cr.execute('UPDATE ir_rule SET domain_force = %s WHERE id = %s', (domain, row[0]))
