import {patch} from "@web/core/utils/patch";
import {PosOrder} from "@point_of_sale/app/models/pos_order";

const {DateTime} = luxon;

patch(PosOrder.prototype, {
    _programIsApplicable(program) {
        if (
            program.trigger === "auto" &&
            !program.rule_ids.find(
                (rule) =>
                    rule.mode === "auto" || this.uiState.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (
            program.trigger === "with_code" &&
            !program.rule_ids.find((rule) =>
                this.uiState.codeActivatedProgramRules.includes(rule.id)
            )
        ) {
            return false;
        }
        if (program.is_nominative && !this.get_partner()) {
            return false;
        }
        if (program.date_from && program.date_from > DateTime.now()) {
            return false;
        }
        if (program.date_to && program.date_to < DateTime.now()) {
            return false;
        }
        if (program.limit_usage && program.total_order_count >= program.max_usage) {
            return false;
        }
        if (
            program.pricelist_ids.length > 0 &&
            (!this.pricelist_id ||
                !program.pricelist_ids.some((pl) => pl.id === this.pricelist_id.id))
        ) {
            return false;
        }
        return true;
    },

});