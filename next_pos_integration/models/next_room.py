# -*- coding: utf-8 -*-
import base64
from io import BytesIO

from odoo import api, fields, models


class NextRoom(models.Model):
    _inherit = 'next.room'

    def _get_self_order_base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

    def action_generate_qr_code(self):
        """(Re)generates the QR code image + target URL for this room's
        self-order page, e.g. https://.../qr-order/<room_id>/<token>."""
        try:
            import qrcode
        except ImportError:
            raise models.UserError(  # noqa: this mirrors Odoo's own pattern
                'The "qrcode" python package is required. Install it with `pip install qrcode[pil]`.')
        for room in self:
            if not room.qr_code_url:
                token = room._next_qr_token()
                room.qr_code_url = '%s/qr-order/%s/%s' % (room._get_self_order_base_url(), room.id, token)
            img = qrcode.make(room.qr_code_url)
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            room.qr_code = base64.b64encode(buffer.getvalue())

    def _next_qr_token(self):
        self.ensure_one()
        # Deterministic but unguessable-enough token for this scaffold;
        # production deployments should use a signed token (itsdangerous /
        # werkzeug.security) tied to an expiry.
        import hashlib
        return hashlib.sha256(('%s-%s-next-qr' % (self.id, self.create_date)).encode()).hexdigest()[:16]
