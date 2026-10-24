/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

/**
 * `next.reservation` is not one of the models the POS loads into its local
 * related-models graph, so `next_reservation_id` can't be set through the
 * normal many2one field-assignment machinery (that expects an already
 * client-side-known record of the related model). Instead the selected
 * reservation (a plain dict from RoomChargeDialog, see payment_screen_patch.js)
 * is stashed as `roomChargeReservation` - an ordinary instance property,
 * outside the formal field system entirely - and injected into the outgoing
 * payload here, exactly like core's own PosOrder.serializeForORM override
 * does for `last_order_preparation_change` just above this patch.
 */
patch(PosOrder.prototype, {
    serializeForORM(opts = {}) {
        const data = super.serializeForORM(opts);
        if (this.roomChargeReservation) {
            data.next_reservation_id = this.roomChargeReservation.id;
        }
        return data;
    },
});
