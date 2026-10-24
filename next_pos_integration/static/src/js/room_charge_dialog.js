/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Popup opened from the Payment screen when staff click a payment method
 * flagged `next_is_room_charge` ("Bill to Room"). Lets them search an
 * in-house guest stay by room number or guest name and pick it; the result
 * (a plain {id, guest_name, rooms, property_name} dict from
 * next.reservation.pos_search_in_house) is handed back via getPayload.
 *
 * Deliberately does NOT use the POS related-models system to resolve a real
 * next.reservation record - that model isn't part of the POS's local data
 * graph, so it is searched over plain RPC instead (see setup()).
 */
export class RoomChargeDialog extends Component {
    static template = "next_pos_integration.RoomChargeDialog";
    static components = { Dialog };
    static props = {
        propertyId: { type: [Number, Boolean], optional: true },
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ term: "", results: [], loading: false, searched: false });
        this.search();
    }

    async search() {
        this.state.loading = true;
        try {
            this.state.results = await this.orm.call("next.reservation", "pos_search_in_house", [
                this.props.propertyId || false,
                this.state.term,
            ]);
        } finally {
            this.state.loading = false;
            this.state.searched = true;
        }
    }

    onInput(ev) {
        this.state.term = ev.target.value;
        this.search();
    }

    selectReservation(reservation) {
        this.props.getPayload(reservation);
        this.props.close();
    }

    get noResultsMessage() {
        return this.state.term
            ? _t("No in-house guest matches that search.")
            : _t("No in-house guests found for this property.");
    }
}
