import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { onMounted } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup?.();
        onMounted(() => {
            let container = document.querySelector('.eft-qr-container');
            if (!container) {
                container = document.createElement('div');
                container.className = 'eft-qr-container';
                container.style.textAlign = 'center';
                container.style.marginTop = '20px';

                const parent = document.querySelector('.payment-buttons');
                if (parent) {
                    parent.appendChild(container);
                    console.log("QR container added to DOM");
                } else {
                    console.warn("Could not find .payment-buttons container");
                    return;
                }
            }
            const order = this.pos.get_order?.();
            const line = order?.get_paymentlines?.().find(
                (line) => line.payment_method.use_payment_interface && line.eft_qr_url
            );

            if (line && line.eft_qr_url) {
                container.innerHTML = '';
                const img = document.createElement('img');
                img.src = line.eft_qr_url;
                img.style.width = '250px';
                img.style.marginTop = '10px';

                container.appendChild(img);
            } else {
                console.warn("No EFT payment line with QR code found");
            }
        });
    },
});
