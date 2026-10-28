# -*- coding: utf-8 -*-
"""Back-fills the new domain_force on three pre-existing Property Owner
ir.rule records (rule_next_room_owner, rule_next_reservation_owner,
rule_next_folio_owner). Those rules were seeded via noupdate="1" data, so
re-shipping a new domain_force in the XML (done in this same release) only
reaches a *fresh* install - an already-installed database keeps the old,
narrower domain (next.room.owner_id only, never the owning property's
owner_ids) until this runs.

Without this, a property owner onboarded the documented way - "Is Property
Owner" + Owned Properties on their contact, with next.room.owner_id never
touched - could see their property on the Owner Portal but not a single
room, reservation or folio inside it: every read of next.room/
next.reservation/next.folio was filtered down to nothing by the old rule.

The two brand-new rules shipped alongside these (rule_next_folio_line_owner,
rule_next_folio_payment_owner) need no migration step - they have no
existing ir_model_data row yet, so the normal module-upgrade data load
creates them fresh regardless of noupdate."""

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
