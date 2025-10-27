/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/payment/payment_interface";
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import { rpc } from "@web/core/network/rpc";

export class PaymentEFT extends PaymentInterface {
    async send_payment_request(cid) {
        const order = this.pos.get_order();
        const line = order.get_selected_paymentline();
        try {
            line.set_payment_status("pending");

            const response = await rpc("/eft/payment/start", {
                amount: line.amount,
                order_id: order.uid || order.name || order.id,
                method_id : line.payment_method_id.id
            });

            if (response.qr_code_base64) {
                line.eft_qr_url = response.qr_code_base64;
                return [true, response.qr_code_base64];
            } else if (response.qr_url) {
                line.eft_qr_url = response.qr_url;
                return [true, response.qr_url];
            } else {
                console.warn("No QR code returned:", response);
                line.set_payment_status("retry");
                return false;
            }
        } catch (error) {
            console.error("EFT Payment Error:", error);
            line.set_payment_status("retry");
            return false;
        }
    }
}

const EFT_TERMINALS = ["alipay", "wechat", "fps", "payme", "unionpay"];
for (const terminal of EFT_TERMINALS) {
    register_payment_method(terminal, PaymentEFT);
}
