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

    onDoFullRefund() {
        const order = this.getSelectedOrder();
        if (!order) return;

        for (const line of order.lines) {
            const refundableQty = line.qty - (line.refunded_qty || 0);
            if (refundableQty <= 0) continue;
            const detail = this.getToRefundDetail(line);
            if (detail.destionation_order_id) continue;
            detail.qty = refundableQty;
        }
        if (this.numberBuffer && this.numberBuffer.reset) {
            this.numberBuffer.reset();
        }
    },

    hasFullRefundCandidates() {
        const order = this.getSelectedOrder();
        if (!order) return false;
        for (const line of order.lines) {
            if ((line.qty - (line.refunded_qty || 0)) > 0) {
                const detail = this.getToRefundDetail(line);
                if (!detail.destionation_order_id) return true;
            }
        }
        return false;
    },
});
