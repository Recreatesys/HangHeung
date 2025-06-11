/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { OmniPrinter } from "./printer";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    afterProcessServerData() {
        var self = this;
        return super.afterProcessServerData(...arguments).then(function () {
            if (self.config.use_omni_print) {
                self.hardwareProxy.printer = new OmniPrinter({ pos: self });
                self.config.iface_cashdrawer = self.config.omni_print_enable_cashdrawer;
            }

        });
    },
    create_printer(config) {
        if (config.use_omni_print) {
            return new OmniPrinter({ pos: this });
        } else {
            return super.create_printer(...arguments)
        }
    },
});
