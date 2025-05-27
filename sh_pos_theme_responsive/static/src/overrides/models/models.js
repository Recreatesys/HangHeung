/** @odoo-module */

import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PosOrderline.prototype, {
    set_quantity(quantity, keep_price) {
        let res = super.set_quantity(quantity, keep_price);
        let self = this
        if(this.models['sh.pos.theme.settings'] && this.models['sh.pos.theme.settings'].getAll()[0] && this.models['sh.pos.theme.settings'].getAll()[0].display_product_cart_qty){
            let orderlines = Object.values(this.order_id.get_orderlines())

            let other_line_with_same_product = orderlines.filter((x) => (x.product_id.id == self.product_id.id && x != self))
            
            if (other_line_with_same_product.length > 0) {
                
                let total_qty = 0
                // other_line_with_same_product.map((x) => total_qty += x.qty)
                total_qty += self.qty
                if (this.order_id.product_with_qty) {
                    this.order_id.product_with_qty[this.product_id.id] = total_qty != 0 ? total_qty : false;
                } else {
                    this.order_id.product_with_qty = {}
                    this.order_id.product_with_qty[this.product_id.id] = total_qty != 0 ? total_qty : false;
                }
                this.order_id['product_with_qty']
            } else {
                if (this.order_id.product_with_qty) {
                    this.order_id.product_with_qty[this.product_id.id] = this.qty != 0 ? this.qty : false
                } else {
                    this.order_id.product_with_qty = {};
                    this.order_id.product_with_qty[this.product_id.id] = this.qty != 0 ? this.qty : false
                }
            }
        }
        return res
    },
    getDisplayData() {
        return {
            ...super.getDisplayData(),
            product_id: this.get_product().id,
            write_date: this.get_product().write_date
        };
    },
});

patch(Orderline, {
    props: {
        ...Orderline.props,
        line: {
            ...Orderline.props.line,
            shape: {
                ...Orderline.props.line.shape,
                product_id: { type: Number, optional: true },
                write_date: {type: String, optional: true}
            },
        },
    },
});
