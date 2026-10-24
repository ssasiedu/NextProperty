/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { RoomChargeDialog } from "@next_pos_integration/js/room_charge_dialog";

patch(PaymentScreen.prototype, {
    /**
     * Intercepts clicking a payment method flagged `next_is_room_charge`
     * ("Bill to Room"): instead of adding a normal tender line straight
     * away, it opens RoomChargeDialog to pick the guest stay first. Picking
     * one stores it on the order (read by the PosOrder JS model patch's
     * serializeForORM override, which is what actually gets it to the
     * backend) and then falls through to the normal payment-line flow so
     * the method still shows up as a tender for the full amount due.
     * Cancelling the dialog adds no payment line at all.
     */
    async addNewPaymentLine(paymentMethod) {
        if (!paymentMethod.next_is_room_charge) {
            return super.addNewPaymentLine(...arguments);
        }

        const reservation = await makeAwaitable(this.dialog, RoomChargeDialog, {
            propertyId: this.pos.config.next_property_id || false,
        });
        if (!reservation) {
            // Dialog was cancelled/closed without a selection.
            return false;
        }

        this.currentOrder.roomChargeReservation = reservation;
        const added = await super.addNewPaymentLine(...arguments);
        if (added) {
            this.notification.add(
                `Billed to Room ${reservation.rooms} - ${reservation.guest_name}`,
                { type: "success" }
            );
        }
        return added;
    },
});
