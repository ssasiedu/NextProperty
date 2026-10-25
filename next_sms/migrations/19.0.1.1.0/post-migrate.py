# -*- coding: utf-8 -*-
"""Back-fills email_subject/email_body on the 18 built-in trigger templates
for an already-installed database. Those template records were seeded via
noupdate="1" data, so re-shipping new field values in the XML (done in this
same release) only reaches a *fresh* install - an existing database keeps
the old rows untouched on upgrade. This one-off script fills in only the
rows that are still missing an email_subject, so it never overwrites a value
an administrator has since edited by hand through the UI."""

EMAIL_DEFAULTS = {
    'booking_confirmation': (
        'Your booking at {property_name} is confirmed',
        '<p>Hi {guest_name},</p><p>Your booking at <strong>{property_name}</strong> '
        'for {date_from} to {date_to} is confirmed. See you soon!</p>'),
    'booking_reminder': (
        'Reminder: your check-in at {property_name} is tomorrow',
        '<p>Hi {guest_name},</p><p>This is a reminder that your check-in at '
        '<strong>{property_name}</strong> is tomorrow ({date_from}).</p>'),
    'booking_cancellation': (
        'Your booking at {property_name} has been cancelled',
        '<p>Hi {guest_name},</p><p>Your booking at <strong>{property_name}</strong> '
        'has been cancelled.</p>'),
    'checkin_complete': (
        'Welcome to {property_name}!',
        "<p>Welcome {guest_name}!</p><p>You're checked into room {room_number}. "
        'Wi-Fi details are on your room card. Enjoy your stay!</p>'),
    'checkout_complete': (
        'Your final bill - room {room_number}',
        "<p>Thank you {guest_name}!</p><p>You've checked out of room {room_number}. "
        'Final folio amount: <strong>{amount}</strong>.</p>'),
    'checkout_discrepancy': (
        'Inventory discrepancy at checkout - room {room_number}',
        '<p>Inventory discrepancy at checkout for room {room_number} ({guest_name}): '
        '<strong>{amount}</strong> charged.</p>'),
    'qr_order_received': (
        'Your order has been received',
        '<p>Your order for room {room_number} ({amount}) has been received and sent '
        'to the kitchen/service team.</p>'),
    'qr_order_ready': (
        'Your order is ready',
        '<p>Your order for room {room_number} is ready!</p>'),
    'housekeeping_room_ready': (
        'Room {room_number} is ready',
        '<p>Room {room_number} has been cleaned and is now ready for sale.</p>'),
    'housekeeping_task_overdue': (
        'Housekeeping task overdue - room {room_number}',
        '<p>Housekeeping task for room {room_number} is overdue. Please check.</p>'),
    'maintenance_new_ticket': (
        'New maintenance ticket - room {room_number}',
        '<p>New maintenance ticket logged for room {room_number}: {guest_name}.</p>'),
    'maintenance_status_update': (
        'Maintenance update - room {room_number}',
        '<p>Maintenance update for room {room_number}: status is now '
        '<strong>{status}</strong>.</p>'),
    'owner_net_revenue_published': (
        'New net revenue statement for {property_name} ({period})',
        '<p>A new net revenue statement for <strong>{property_name}</strong> ({period}) '
        'has been published.</p><p>Amount: <strong>{amount}</strong>.</p>'
        '<p>Log in to the Owner Portal to view the full statement and its trend.</p>'),
    'owner_viewing_requested': (
        'Viewing requested at {property_name}',
        '<p>A property viewing has been requested at <strong>{property_name}</strong> '
        'for {date_from}.</p>'),
    'owner_viewing_confirmed': (
        'Your viewing at {property_name} is confirmed',
        '<p>Your property viewing at <strong>{property_name}</strong> is confirmed '
        'for {date_from}.</p>'),
    'owner_room_status_change': (
        'Room {room_number} status change',
        '<p>Room {room_number} at {property_name} changed status to '
        '<strong>{status}</strong>.</p>'),
    'channel_ota_booking_received': (
        'New OTA booking via {channel}',
        '<p>New OTA booking received via <strong>{channel}</strong> for {property_name}: '
        '{date_from} to {date_to}.</p>'),
    'auth_otp': (
        'Your verification code',
        '<p>Your NEXT Property Management verification code is <strong>{otp}</strong>.</p>'
        '<p>If you did not request this, you can ignore this email.</p>'),
}


def migrate(cr, version):
    # Plain SQL, not the ORM: migration scripts run before the registry for
    # this module's models is guaranteed loaded, so we update the table
    # directly - the two columns already exist by this point since the ORM
    # schema sync for this module's own new fields runs before post-migrate.
    cr.execute("SELECT id, trigger_code FROM next_sms_template WHERE email_subject IS NULL OR email_subject = ''")
    rows = cr.fetchall()
    for row_id, trigger_code in rows:
        defaults = EMAIL_DEFAULTS.get(trigger_code)
        if not defaults:
            continue
        subject, body_html = defaults
        cr.execute(
            'UPDATE next_sms_template SET email_subject = %s, email_body = %s WHERE id = %s',
            (subject, body_html, row_id),
        )
