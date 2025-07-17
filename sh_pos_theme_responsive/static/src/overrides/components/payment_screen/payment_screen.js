/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


patch(PaymentScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    async addNewPaymentLine(paymentMethod) {
        const result = this.pos.get_order().add_paymentline(paymentMethod);

        if (result === "__BLOCK_OVERPAY__") {
            await this.dialog.add(AlertDialog, {
                title: _t("Invalid Payment"),
                body: _t("You have already paid more than to the total amount. Please remove extra payments before adding another one."),
            });
            return;
        }
        return result;
    }
});
