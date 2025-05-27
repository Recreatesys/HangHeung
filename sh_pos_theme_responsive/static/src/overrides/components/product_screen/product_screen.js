/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(ProductScreen.prototype, {
    
    setup() {
        super.setup()
        onMounted(this.onMounted);
        this.pos = usePos();
        this.pos.isMobile = false
        setTimeout(() => {

            var owl = $('.owl-carousel');
            owl.owlCarousel({
                loop: false,
                nav: true,
                margin: 10,
                responsive: {
                    0: {
                        items: 1
                    },
                    600: {
                        items: 3
                    },
                    960: {
                        items: 5
                    },
                    1200: {
                        items: 6
                    }
                }
            });
            owl.on('mousewheel', '.owl-stage', function (e) {
                if (e.originalEvent.wheelDelta > 0) {
                    owl.trigger('next.owl');
                } else {
                    owl.trigger('prev.owl');
                }
                e.preventDefault();
            });
        }, 20);
    },
    onMounted() {
        
        if(this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position != 'bottom'){
            $($('.btn-light.flex-shrink-0')[1]).addClass('233')
        }
        if($('.btn-light.flex-shrink-0') && $('.btn-light.flex-shrink-0').length > 0){
            $($('.btn-light.flex-shrink-0')[2]).addClass('sh_hide_button')
            $($('.btn-light.flex-shrink-0')[3]).addClass('789')
            $($('.btn-light.flex-shrink-0')[4]).addClass('910')
            $($('.btn-light.flex-shrink-0')[5]).addClass('125')
        }
        if(this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_cart_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_cart_position == 'right_side'){
            document.getElementsByClassName('product-screen')[0].insertBefore(document.getElementsByClassName('leftpane')[0],document.getElementsByClassName('rightpane')[0]);
        }
        if(this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'bottom' && document.getElementsByClassName('product-screen')[0]){
            document.getElementsByClassName('product-screen')[0].classList.add('sh_control_button_bottom')
        }else if(this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'left_side' && document.getElementsByClassName('product-screen')[0]){
            document.getElementsByClassName('product-screen')[0].classList.add('sh_control_button_left')
        }else if(this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'right_side' && document.getElementsByClassName('product-screen')[0]){
            document.getElementsByClassName('product-screen')[0].classList.add('sh_control_button_right')
        }

        if(this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_pos_switch_view){
            if(this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_default_view == 'grid_view' && document.getElementsByClassName('product_grid_view')[0] && document.getElementsByClassName('sh_product_list_view')[0]){
                document.getElementsByClassName('product_grid_view')[0].classList.add('highlight')
                document.getElementsByClassName('sh_product_list_view')[0].classList.add('hide_sh_product_list_view')
            }
            if(this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_default_view == 'list_view' && document.getElementsByClassName('product_list_view')[0] && document.getElementsByClassName('product-list')[1]){
                document.getElementsByClassName('product_list_view')[0].classList.add('highlight')
                document.getElementsByClassName('product-list')[1].classList.add('hide_product_list_container')
            }
        }
        if(this.ui.isSmall){
            this.pos.isMobile = true
            if(document.getElementsByClassName('sh_product_list_view').length > 0 && document.getElementsByClassName('sh_product_list_view')[0]){
                document.getElementsByClassName('sh_product_list_view')[0].classList.add('hide_sh_product_list_view')
            }
            if(document.getElementsByClassName('product-list').length > 0 && document.getElementsByClassName('product-list')[1]){
                document.getElementsByClassName('product-list')[1].classList.remove('hide_product_list_container')
            }
        }
        if($('.control-buttons') && $('.control-buttons').length > 0){
            for (const each_control_button of $('.control-buttons')) {
                if($(each_control_button)[0] && $($(each_control_button)[0]) && $($(each_control_button)[0]).children()){
                    for (const each_children of $($(each_control_button)[0]).children()) {
                        if($(each_children) && !$(each_children).hasClass('sh_hide_button')){
                            if(this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'bottom'){
                                $('.sh_action_button').append(each_children)
                            }else{
                                $('.control-buttons-modal').append(each_children)
                            }
                        }
                    }
                }

            }
        }
    }
});
