/** @odoo-module **/

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextInputPopup } from "@point_of_sale/app/utils/input_popups/text_input_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    async clickPromoCode() {
        const order = this.pos.get_order();

        this.dialog.add(TextInputPopup, {
            title: _t("Enter Code"),
            placeholder: _t("Gift card or Discount code"),
            getPayload: async (code) => {
                code = code.trim();
                if (code === "") return;

                const orderLines = order.get_orderlines();
                const discountConfigs = this.pos.models['discount.config'] || [];

                let hasExclusive = false;

                for (const line of orderLines) {
                    const matchedConfig = discountConfigs.find(
                        (cfg) => cfg.discount_product.id === line.product_id.id
                    );

                    // If any order line matches an exclusive discount config, block further discounts
                    if (matchedConfig?.is_exclusive_discount) {
                        hasExclusive = true;
                        break;
                    }
                }

                // ✅ Block if an exclusive discount is already applied
                if (hasExclusive) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Discount already applied"),
                        body: _t(
                            "You cannot apply a coupon because an exclusive discount is already applied on this order."
                        ),
                    });
                    return;
                }

                // ✅ Otherwise, allow coupon code application
                const res = await this.pos.activateCode(code);
                if (res !== true) {
                    this.notification.add(res, { type: "danger" });
                }
            },
        });
    },
});
