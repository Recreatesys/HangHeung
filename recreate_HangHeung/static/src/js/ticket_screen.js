/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async onDoRefund() {
        const order = this.getSelectedOrder();
        if (order) {
            this.pos._refund_source_order_id = order.backendId || order.id;
            this.pos._refund_source_order_name = order.name;
        }

        await super.onDoRefund();
    },

    async _setOrder(order) {
        if (order && order.finalized) {
            this.setSelectedOrder(order);
            return;
        }
        await super._setOrder(order);
    },
});
