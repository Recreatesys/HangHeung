/** @odoo-module **/
/**
 * Receipt extension: when a POS order is settling a sale.order, surface
 * 取貨日期 (commitment_date) and 取貨地點 (partner_shipping_id) on the receipt.
 *
 * Both values are server-rendered as plain Char strings on sale.order
 * (pickup_date_display, pickup_address_display) and added to the POS
 * loader via _load_pos_data_fields. This avoids relying on the
 * partner_shipping_id record being in POS state -- internal-shop
 * partners are filtered out by the POS group ir.rule.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    export_for_printing(baseUrl, headerData) {
        const data = super.export_for_printing(...arguments);
        const lineWithSO = this.lines.find((l) => l.sale_order_origin_id);
        if (lineWithSO && lineWithSO.sale_order_origin_id) {
            const so = lineWithSO.sale_order_origin_id;
            if (so.pickup_date_display) {
                data.recreate_pickup_date = so.pickup_date_display;
            }
            if (so.pickup_address_display) {
                data.recreate_pickup_address = so.pickup_address_display;
            }
        }
        // Collect distinct coupon codes redeemed in this order so the
        // receipt can list them under "已用優惠券". Reward orderlines carry
        // coupon_id (a loyalty.card) whose `code` is loaded into POS state
        // when the code is scanned via use_coupon_code.
        const seen = new Set();
        const usedCoupons = [];
        for (const line of this.lines) {
            const card = line.coupon_id;
            if (!card || !card.code || seen.has(card.id)) {
                continue;
            }
            seen.add(card.id);
            usedCoupons.push({
                code: card.code,
                program: (card.program_id && card.program_id.name) || "",
            });
        }
        if (usedCoupons.length) {
            data.recreate_used_coupons = usedCoupons;
        }
        return data;
    },
});
