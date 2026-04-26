/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    closeScreen() {
        this.addOrderIfEmpty();
        const order = this.get_order();
        const screenData = order ? order.get_screen_data() : {};
        let screenName = screenData?.name;
        const props = {};
        if (screenName === "PaymentScreen") {
            props.orderUuid = this.selectedOrderUuid;
        }
        if (!screenName) {
            if (order && order.finalized) {
                screenName = "ReceiptScreen";
            } else {
                screenName = "ProductScreen";
            }
        }
        this.showScreen(screenName, props);
    },
});
