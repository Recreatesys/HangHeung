/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { session } from "@web/session";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { Popup } from "@eg_pos_restrict_stock/js/Popup";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";


patch(ProductScreen.prototype, {
    async _processData(loadedData) {
         await super._processData(...arguments);
         this.product_template = loadedData['product.template'];
          this.product_product = loadedData['product.product'];
    },
    setup() {
        super.setup(...arguments);
        this.setProductQty()
    },
    async setProductQty() {
       this.env.services.pos.get_order().get_orderlines().forEach(function (line) {

                line.product_id.qty_available -= line.qty
        });

    },
    async addProductToOrder(product, options = {}) {
                var self = this;

                // HH-CUSTOM: bypass the out-of-stock gate for combos and
                // phantom-BOM kits -- their qty_available is structurally
                // 0 because real availability is on the choices/components.
                if (product.pos_stock_skip_check) {
                    return super.addProductToOrder(...arguments);
                }

                if(product.qty_available <= 0 && this.env.services.pos.config.restrict_product){
                     product.add_forcefully = true;

                     this.dialog.add(Popup, {
                           'Product': product,
                           'product_name': product.display_name,
                    });
                }else{
                    super.addProductToOrder(...arguments);
                     product.qty_available -= 1;
                }
            }

});


patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
    },
     set_quantity(quantity, keep_price) {
        // HH-CUSTOM: skip the qty cap for combos / phantom-BOM kits.
        if (this.product_id.pos_stock_skip_check) {
            return super.set_quantity(quantity, keep_price);
        }
        var quantity_product = this.qty + this.product_id.qty_available;
        if(quantity && quantity_product < quantity && !this.product_id.add_forcefully){
          return {
//                    super.set_quantity(quantity, keep_price);
                    title: ("Qty is Limit."),
                    body: ('Out of Stock '+ this.product_id.display_name + "." ),
                };
            }
                else{
                    return super.set_quantity(quantity, keep_price);}
     }
});



patch(PaymentScreen.prototype, {
     validateOrder(isForceValidate) {
        super.validateOrder(...arguments);
        this.pos.get_order().get_orderlines().forEach(function (line) {
            if(line.product_id.add_forcefully){
               line.product_id.qty_available -= line.qty
               line.product_id.qty_available += 1;
            }
        });
    }
});
