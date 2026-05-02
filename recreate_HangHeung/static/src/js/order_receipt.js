/** @odoo-module **/
/**
 * Receipt extension: when a POS order is settling a sale.order, surface
 * 取貨日期 (commitment_date) and 取貨地點 (partner_shipping_id) on the receipt.
 *
 * The pos_sale module loads sale_order_origin_id on each pos.order.line.
 * recreate_HangHeung._load_pos_data_fields adds commitment_date to the
 * sale.order POS payload. partner_shipping_id is loaded as a reference
 * to a res.partner whose `name` and `street`/`city`/`contact_address` are
 * available in POS state.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

function _formatDate(value) {
    if (!value) return null;
    if (typeof value === "string") {
        // Trim trailing seconds when ISO-like
        return value.replace("T", " ").slice(0, 16);
    }
    if (value && typeof value.toFormat === "function") {
        try {
            return value.toFormat("yyyy-LL-dd HH:mm");
        } catch (e) {
            return String(value);
        }
    }
    if (value && typeof value.toString === "function") {
        return String(value);
    }
    return null;
}

function _formatAddress(partner) {
    if (!partner) return null;
    const fields = [
        partner.name || "",
        partner.street || "",
        partner.street2 || "",
        partner.city || "",
    ];
    const cleaned = fields.map((s) => (s || "").toString().trim()).filter(Boolean);
    if (!cleaned.length) return null;
    return cleaned.join(" — ");
}

patch(PosOrder.prototype, {
    exportForPrinting() {
        const data = super.exportForPrinting(...arguments);
        const lineWithSO = this.lines.find((l) => l.sale_order_origin_id);
        if (lineWithSO && lineWithSO.sale_order_origin_id) {
            const so = lineWithSO.sale_order_origin_id;
            const pickupDate = _formatDate(so.commitment_date);
            if (pickupDate) {
                data.recreate_pickup_date = pickupDate;
            }
            const pickupAddress = _formatAddress(so.partner_shipping_id);
            if (pickupAddress) {
                data.recreate_pickup_address = pickupAddress;
            }
        }
        return data;
    },
});
