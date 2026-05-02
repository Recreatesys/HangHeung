/** @odoo-module **/
/**
 * Receipt extension: when a POS order is settling a sale.order, surface
 * 取貨日期 (commitment_date) and 取貨地點 (partner_shipping_id) on the receipt.
 *
 * The pos_sale module already loads sale_order_origin_id on each pos.order.line.
 * We pluck commitment_date and partner_shipping_id from the first matching line
 * and stash them on the data object that the receipt template reads.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    exportForPrinting() {
        const data = super.exportForPrinting(...arguments);
        const lineWithSO = this.lines.find((l) => l.sale_order_origin_id);
        if (lineWithSO && lineWithSO.sale_order_origin_id) {
            const so = lineWithSO.sale_order_origin_id;
            data.recreate_pickup_date = so.commitment_date || so.shipping_date || null;
            const ship = so.partner_shipping_id;
            if (ship) {
                const parts = [
                    ship.name || "",
                    ship.contact_address || ship.street || "",
                ].filter((p) => p && p.trim());
                data.recreate_pickup_address = parts.join(" — ") || null;
            }
        }
        return data;
    },
});
