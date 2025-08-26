
/** @odoo-module **/

import { SMLX2ManyField } from "@stock/fields/stock_move_line_x2_many_field";
import { patch } from "@web/core/utils/patch";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";

patch(SMLX2ManyField.prototype, {
    async onAdd({ context, editable } = {}) {
        const productId = this.props.record.data.product_id?.[0];
        const pickingId = this.props.record.data.picking_id?.[0];
        const defaultLocation = this.props.context.default_location_id;

        const wizardAction = {
            type: 'ir.actions.act_window',
            name: _t("Add Line Wizard"),
            res_model: 'stock.move.add.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_quantity: 1,
                default_product_id: productId,
                default_picking_id: pickingId,
                default_from_location: defaultLocation,
            },
        };
        const wizardPromise = this.env.services.action.doAction(wizardAction);

        const quantContext = {
            ...context,
            single_product: true,
            list_view_ref: "stock.view_stock_quant_tree_simple",
            search_default_on_hand: true,
            search_default_in_stock: true,
        };

        const productName = this.props.record.data.product_id?.[1];
        const title = _t(`Add line: ${productName}`);

        let domain = [
            ["product_id", "=", productId],
            ["location_id", "child_of", defaultLocation],
        ];

        if (this.dirtyQuantsData.size) {
            const notFullyUsed = [];
            const fullyUsed = [];
            for (const [quantId, quantData] of this.dirtyQuantsData.entries()) {
                if (quantData.available_quantity > 0) {
                    notFullyUsed.push(quantId);
                } else {
                    fullyUsed.push(quantId);
                }
            }
            if (fullyUsed.length) {
                domain = Domain.and([domain, [["id", "not in", fullyUsed]]]).toList();
            }
            if (notFullyUsed.length) {
                domain = Domain.or([domain, [["id", "in", notFullyUsed]]]).toList();
            }
        }
        const selectCreatePromise = this.selectCreate({ domain, context: quantContext, title });
        const wizardResult = await wizardPromise;
        if (!wizardResult) return selectCreatePromise; 

        let wizardData = await this.orm.read(
            'stock.move.add.wizard',
            [wizardResult.res_id],
            ['quantity', 'from_location']
        );
        wizardData = wizardData[0];
        if (!wizardData) return selectCreatePromise;

        const { quantity, from_location } = wizardData;
        quantContext.wizard_quantity = quantity;
        quantContext.wizard_from_location = from_location?.[0] || defaultLocation;
        return selectCreatePromise;
    },
});


