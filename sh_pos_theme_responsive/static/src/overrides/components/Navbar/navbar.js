/** @odoo-module */

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";


patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
        onMounted(this.onMounted);
    },
    onMounted() {
        var self = this
        setTimeout(() => {
            if (localStorage.getItem("sh_pos_night_mode") == 'true') {
                document.getElementsByClassName("pos")[0].classList.add("sh_pos_night_mode")
                localStorage.setItem("sh_pos_night_mode", true)
                self.sh_pos_night_mode = true
            }
            if(self.pos && self.pos.config && self.pos.config.sh_pos_night_mode){
                 if (localStorage.getItem("sh_pos_night_mode") == 'true') {
                    localStorage.setItem("sh_pos_night_mode", true)
                }
                else{
                    localStorage.setItem("sh_pos_night_mode", true)
                }
            }
        }, 500);
    },
    change_mode(){
        if(this.pos.config.sh_pos_night_mode){
            document.getElementsByClassName('pos')[0].classList.toggle("sh_pos_night_mode")
            if(document.getElementsByClassName('icon-moon')[0].classList.contains('fa-sun-o')){
                document.getElementsByClassName('icon-moon')[0].classList.remove('fa-sun-o')
                document.getElementsByClassName('icon-moon')[0].classList.add('fa-moon-o')
            }else{
                document.getElementsByClassName('icon-moon')[0].classList.add('fa-sun-o')
                document.getElementsByClassName('icon-moon')[0].classList.remove('fa-moon-o')
            }
            // $(".icon-moon").toggleClass("fa-sun-o fa-moon-o")
            localStorage.setItem("sh_pos_night_mode", document.getElementsByClassName('pos')[0].classList.contains("sh_pos_night_mode"))
        }
    },
    get cart_item_count(){
        if(this && this.pos && this.pos.models['sh.pos.theme.settings'] && this.pos.models['sh.pos.theme.settings'].getAll()[0].display_cart_order_item_count && this.pos.get_order()){
            return this.pos.get_order().get_orderlines().length
        }else{
            return 0
        }
    }
});
