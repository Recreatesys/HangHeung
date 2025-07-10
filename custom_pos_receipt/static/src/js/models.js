/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    getReceiptHeaderData(order) {
        if (!order || !order.lines) {
          return super.getReceiptHeaderData(...arguments);
        }
        const totalQty = order.lines.reduce(
            (sum, line) => {
                if (!line.is_reward_line && line.product_id.type !== "service" &&
                (!line.combo_line_ids || line.combo_line_ids.length === 0)) {
                    return sum + (parseFloat(line.qty) || 0);
                }
                return sum;
            },
            0
        );
        return {
            ...super.getReceiptHeaderData(...arguments),
            partner: order.partner_id,
            orderRef: order.name,
            storeName: order.config_id.name,
            storeCashier:order.cashier,
            totalQty: totalQty
        };
    },
});

