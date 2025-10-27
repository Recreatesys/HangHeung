import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    handle_payment_response(isPaymentSuccessful) {
        const qrTerminals = ["alipay", "wechat","fps","payme","unionpay"];
        const terminal = this.payment_method_id.use_payment_terminal;

        if (isPaymentSuccessful[0] && qrTerminals.includes(terminal)) {
            this.set_payment_status("waiting");
            this._showQRCode(isPaymentSuccessful[1]);
        } 
        else if (isPaymentSuccessful[0] && !qrTerminals.includes(terminal)) {
            this.set_payment_status("done");
            if (this.payment_method_id.payment_method_type !== "qr_code") {
                this.can_be_reversed = this.payment_method_id.payment_terminal.supports_reversals;
            }
        }
        else {
            this.set_payment_status("retry");
        }

        return isPaymentSuccessful[0];
    },

    _showQRCode(qrUrl, retryCount = 0) {
        const container = document.querySelector('.eft-qr-container');
        if (!container) {
            if (retryCount < 10) {
                console.warn(`QR container not found. Retrying... (${retryCount + 1})`);
                setTimeout(() => this._showQRCode(qrUrl, retryCount + 1), 100);
            } else {
                console.error("Failed to find QR container after multiple retries.");
            }
            return;
        }

        container.innerHTML = '';
        const img = document.createElement('img');
        img.src = qrUrl;
        img.style.width = '250px';
        img.style.marginTop = '10px';
        container.appendChild(img);
    }
});
