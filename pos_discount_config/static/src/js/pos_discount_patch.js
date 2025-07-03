/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { applyDiscountLogic } from "./discount_utils";


patch(PosStore.prototype, {
    async addLineToCurrentOrder(productInfo, options, configure) {
        const result = await super.addLineToCurrentOrder(...arguments);
        const order = this.get_order();
        if (order) {
            await applyDiscountLogic(order);
        } else {
            console.warn("Order not found.");
            return;
        }
    },
});


patch(PosOrderline.prototype, {
    get is_auto_discount_line() {
        return this.note === "AUTO:discount";
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(),
            customerNote: String(this.customer_note || ""),
        };
    },

    set_quantity(quantity, keep_price) {
        const result = super.set_quantity.call(this, quantity, keep_price);
        const order_id = this.order_id
        this._apply_discount_rule(order_id);
        return result;
    },

    async _apply_discount_rule(order_id) {
         if (order_id) {
            await applyDiscountLogic(order_id);
        } else {
            console.warn("Order not found in set_quantity.");
            return;
        }
    },
});


patch(OrderSummary.prototype, {
    updateSelectedOrderline(event) {
        const order = this.pos.get_order();
        const line = order?.get_selected_orderline();

        if (line?.is_auto_discount_line) {
            return;
        }
        super.updateSelectedOrderline(event);
    },

//    editPackLotLines(line) {
//        if (line?.is_auto_discount_line) {
//            return;
//        }
//        super.editPackLotLines(line);
//    },
});
