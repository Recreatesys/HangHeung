/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(PaymentScreen.prototype, {
    async setup() {
        await super.setup();

        const sourceOrderName = this.pos._refund_source_order_name;
        const sourceOrderId = this.pos._refund_source_order_id;

        if (sourceOrderName) {

            const result = await this.fetchOriginalAndRefundMethod(sourceOrderName, sourceOrderId);
            const refundMethodId = result?.refund_payment_method_id;
            const allPaymentMethods = this.pos.config.payment_method_ids || [];

            const refundMethod = allPaymentMethods.find(pm => pm.id === refundMethodId);

            if (refundMethod) {
                this.payment_methods_from_config = [refundMethod];
            } else {
                this.payment_methods_from_config = allPaymentMethods;
                // this.payment_methods_from_config = [];
            }

            // Cleanup
            delete this.pos._refund_source_order_id;
            delete this.pos._refund_source_order_name;
        } else {
            // Fallback for normal sales
            const allPaymentMethods = this.pos.config.payment_method_ids || [];
            this.payment_methods_from_config = allPaymentMethods.slice().sort((a, b) => a.sequence - b.sequence);
        }
    },

    async fetchOriginalAndRefundMethod(orderName, orderId) {
        try {
            const result = await rpc("/pos/get_payment_method_by_name", {
                name: orderName,
                id: orderId,
            });
            console.log("[Refund Filter] Backend result:", result);
            return result;
        } catch (error) {
            console.error("[Refund Filter] RPC Error:", error);
            return {};
        }
    },
});
