/** @odoo-module **/

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    add_paymentline(payment_method) {
        this.assert_editable();

        if (this.electronic_payment_in_progress()) {
            return false;
        }

        const totalAmountDue = this.getDefaultAmountDueToPayIn(payment_method);

        if (totalAmountDue <= 0) {
            return "__BLOCK_OVERPAY__";
        }

        const newPaymentline = this.models["pos.payment"].create({
            pos_order_id: this,
            payment_method_id: payment_method,
        });
        this.select_paymentline(newPaymentline);
        newPaymentline.set_amount(totalAmountDue);

        if (
            payment_method.payment_terminal ||
            payment_method.payment_method_type === "qr_code"
        ) {
            newPaymentline.set_payment_status("pending");
        }

        return newPaymentline;
    }
});
