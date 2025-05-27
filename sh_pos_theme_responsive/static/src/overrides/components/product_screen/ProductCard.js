/** @odoo-module */

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ProductCard.prototype, {
    setup() {
        super.setup()
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    }
});
