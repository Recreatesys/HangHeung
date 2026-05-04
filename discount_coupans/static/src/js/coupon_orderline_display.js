/** @odoo-module **/
/**
 * Show the redeemed coupon code on the POS orderline display so the
 * cashier can verify which physical coupon produced each reward line
 * during the transaction. Format: "<reward name> [<code>]".
 *
 * Patches PosOrderline.getDisplayData -- the same method core POS uses
 * to render lines on both the orderline list and the receipt, so the
 * receipt's reward lines will also carry the code suffix (kept in
 * addition to the dedicated 已用優惠券 footer block for clarity).
 */
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";

patch(PosOrderline.prototype, {
    getDisplayData() {
        const data = super.getDisplayData();
        const code = this.coupon_id && this.coupon_id.code;
        if (this.reward_id && code) {
            data.productName = `${data.productName} [${code}]`;
        }
        return data;
    },
});
