# -*- coding: utf-8 -*-
"""Simplifies the five Property Owner ir.rule domains added/widened in
19.0.1.1.0: that release required next.room.owner_id to be explicitly
False for the property-level ownership fallback to count at all. That's
backwards - property-level ownership (next.property.owner_ids, the entire
documented onboarding flow) must always be sufficient on its own. A
stray/stale owner_id value left on a room from earlier manual testing
(pointing at some other, or by-then-deleted, contact) silently blocked
BOTH branches of the old domain - the direct one (owner_id doesn't match)
and the fallback one (owner_id isn't False) - which is exactly the "403:
doesn't have 'read' access to Room" a property owner who could already see
their own Property hit on the very first thing that touches a room (the
Net Revenue page's room column).

These rules are noupdate="1" data, same as in 19.0.1.1.0 - and crucially,
by the time this runs, all five already exist in every database that ran
that migration (the two previously-brand-new ones included), so this
updates all five rather than skipping any as "new"."""

DOMAINS = {
    'rule_next_room_owner': (
        "['|', ('owner_id.user_ids', 'in', [user.id]),"
        " ('property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_reservation_owner': (
        "['|', ('room_ids.owner_id.user_ids', 'in', [user.id]),"
        " ('room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_folio_owner': (
        "['|', ('reservation_id.room_ids.owner_id.user_ids', 'in', [user.id]),"
        " ('reservation_id.room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_folio_line_owner': (
        "['|', ('folio_id.reservation_id.room_ids.owner_id.user_ids', 'in', [user.id]),"
        " ('folio_id.reservation_id.room_ids.property_id.owner_ids.user_ids', 'in', [user.id])]"
    ),
    'rule_next_folio_payment_owner': (
        "['|', ('folio_id.reservation_id.room_ids.owner_id.user_ids', 'in', [user.id]),"
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
