/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";

patch(Numpad.prototype, {
    setup() {
        super.setup();
        const _onClick = this.onClick;
        this.onClick = (buttonValue) => {
            _onClick(buttonValue);
            if (buttonValue === "Backspace") {
                _onClick(buttonValue);
            }
        };
    },
});
