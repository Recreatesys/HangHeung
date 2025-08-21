/** @odoo-module **/

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { scheduleDiscountLogic } from "./discount_utils";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async addLineToCurrentOrder(productInfo, options, configure) {
        const result = await super.addLineToCurrentOrder(...arguments);
        const order = this.get_order();
        if (order) {
            scheduleDiscountLogic(order);
        }
        return result;
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
        const order_id = this.order_id;
        if (order_id) {
            scheduleDiscountLogic(order_id);
        }
        return result;
    },
});

patch(OrderSummary.prototype, {
    async updateSelectedOrderline(event) {
        const order = this.pos.get_order();
        const line = order?.get_selected_orderline();

        if (line?.is_auto_discount_line) {
            if (event.key === "Backspace" || event.key === "Delete") {
                const confirmed = await ask(this.dialog, {
                    title: _t("Remove Auto Discount"),
                    body: _t(
                        "Are you sure you want to remove the auto-applied discount?\nIt will not be re-applied unless conditions are met again."
                    ),
                    cancelLabel: _t("No"),
                    confirmLabel: _t("Yes"),
                });
                if (confirmed) {
                    order.removeOrderline(line);
                }else {
                    return;
                }
            }
            return;
        }
        super.updateSelectedOrderline(event);
    },
});
