/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    async _finalizeValidation(...args){
        const result = await super._finalizeValidation(...args);
        try {
            if (this.currentOrder) {
                const customer = this.currentOrder.get_partner();
                const customerName = customer ? customer.name : "Walk-in Customer";
                const customerId = customer ? customer.id : false;
                const storeId = this.currentOrder.config_id.id
                let activatedCoupon = false;
                if (
                    this.currentOrder._code_activated_coupon_ids &&
                    this.currentOrder._code_activated_coupon_ids.length > 0
                ) {
                    activatedCoupon = this.currentOrder._code_activated_coupon_ids[0].code;

                }
                if (activatedCoupon) {
                    await this.env.services.orm.call(
                        "loyalty.card",
                        "update_coupon_redeem_from_pos",
                        [{
                            coupon_code: activatedCoupon,
                            store_id: storeId,

                        }]
                    );
                }
                const orderLines = this.currentOrder.get_orderlines();
                let productData = [];

                for (let line of orderLines) {
                    let productName = line.product_id ? line.product_id.name : "";


                    let lotNames = [];
                    if (line.pack_lot_ids && line.pack_lot_ids.length) {
                        lotNames = line.pack_lot_ids.map(lot => lot.lot_name);
                    }

                    if (lotNames.length > 0) {
                        productData.push({
                            product_name: line.product_id.name,
                            lots: lotNames,
                            customer: customerName,
                            customer_id: customerId,
                        });
                    }
                }
                if (productData.length > 0) {
                    await this.env.services.orm.call(
                        "loyalty.card",
                        "update_loyalty_from_pos",
                        [productData]
                    );
                }
            }
        } catch (err) {
            console.error("Error sending post-payment data:", err);
        }
        return result;
    }
});
