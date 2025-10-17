/** @odoo-module **/
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { PosStore } from "@point_of_sale/app/store/pos_store"

export class Popup extends Component {
        static template = "eg_pos_restrict_stock.Popup";
        static components = { Dialog };
         setup() {
                super.setup();
                        this.pos = usePos();
                        this.orm = useService("orm");
                        this.dialog = useService("dialog");

	    }
        static defaultProps = {
            confirmText: 'Order',
            cancelText: 'Cancel',
            title: 'Product Out of Stock!',
            Product:'',
            product_name:'',
        };

        async add_restrict_product(){
            var self = this;
            var product = this.props.Product;

            await this.pos.addLineToCurrentOrder(
                        { product_id: product},
                    );
            product.qty_available -= 1;
            self.props.close();
        }
         cancel() {
            this.props.close();
        }
}
