/** @odoo-module */

import { CategorySelector } from "@point_of_sale/app/generic_components/category_selector/category_selector";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(CategorySelector.prototype, {
    setup(){
        super.setup();
        this.pos = usePos();
        this.ui = useState(useService("ui"));
    },
    onClickProductGridView(){
        document.getElementsByClassName('product_grid_view')[0].classList.add('highlight')

        document.getElementsByClassName('product-list')[1].classList.remove('hide_product_list_container')

        document.getElementsByClassName('product_list_view')[0].classList.remove('highlight')

        document.getElementsByClassName('sh_product_list_view')[0].classList.add('hide_sh_product_list_view')
    },
    onClickProductListView(){

        document.getElementsByClassName('product_grid_view')[0].classList.remove('highlight')

        document.getElementsByClassName('product-list')[1].classList.add('hide_product_list_container')

        document.getElementsByClassName('product_list_view')[0].classList.add('highlight')

        document.getElementsByClassName('sh_product_list_view')[0].classList.remove('hide_sh_product_list_view')
    },
    isMobile() {
        return this.ui.isSmall
    }
});
