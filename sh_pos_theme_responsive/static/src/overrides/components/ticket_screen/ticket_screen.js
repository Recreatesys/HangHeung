/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(TicketScreen.prototype, {
    setup() {
        super.setup()
        onMounted(this.onMounted);
        this.pos = usePos();
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
        super.onMounted()
        if(this && this.pos && this.pos.models['sh.pos.theme.settings'].getAll() && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_cart_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_cart_position == 'left_side'){
            $('.leftpane').insertBefore($('.rightpane'));
        }
        if(this && this.pos && this.pos.models['sh.pos.theme.settings'].getAll() && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'bottom'){
            $('.ticket-screen').addClass('sh_control_button_bottom')
        }else if(this && this.pos && this.pos.models['sh.pos.theme.settings'].getAll() && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'left_side'){
            $('.ticket-screen').addClass('sh_control_button_left')
        }
        else if(this && this.pos && this.pos.models['sh.pos.theme.settings'].getAll() && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'right_side'){
            $('.ticket-screen').addClass('sh_control_button_right')
        }
        if(this && this.pos && this.pos.models['sh.pos.theme.settings'].getAll() && this.pos.models['sh.pos.theme.settings'].getAll()[0] && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_cart_position && this.pos.models['sh.pos.theme.settings'].getAll()[0].sh_action_button_position == 'bottom'){
            $('.ticket-screen').addClass('sh_hide_control_button_screen')
        }
    },
    get isOrderSynced(){
        var res = super.isOrderSynced
        if (this.state.filter === "SYNCED") {
            $('.ticket-screen').removeClass('sh_hide_control_button_screen')
            $('.sh_action_button').removeClass('sh_hide_action_button')
        }
        return res
    }
});
