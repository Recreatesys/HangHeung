import {patch} from "@web/core/utils/patch";
import {PosStore} from "@point_of_sale/app/store/pos_store";
const {DateTime} = luxon;
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData();
        for (const program of this.models["loyalty.program"].getAll()) {
            // console.log(program, 1111111)
            if (program.date_to) {
                const parts = program.date_to.invalid.explanation.split('"');
                const extractedDate = parts.length >= 2 ? parts[1] : null;
                program.date_to = DateTime.fromFormat(extractedDate, "yyyy-MM-dd HH:mm:ss", {zone: "utc"});
                program.date_to = DateTime.fromISO(program.date_to);
            }
            if (program.date_from) {
                const parts1 = program.date_from.invalid.explanation.split('"');
                const extractedDate1 = parts1.length >= 2 ? parts1[1] : null;
                program.date_from = DateTime.fromFormat(extractedDate1, "yyyy-MM-dd HH:mm:ss", {zone: "utc"});
                program.date_from = DateTime.fromISO(program.date_from);
            }
        }
    },

    async activateCode(code) {
        const order = this.get_order();
        const orderLines = order.get_orderlines();
        const productIds = [];
        for (const line of orderLines) {
            const productId = line.product_id.id;
            productIds.push(productId);
        }
        try {
            const isValid = await rpc("/pos/validate_discount_products", { product_ids: productIds });

            if (!isValid) {
                return _t("One or more products in your order are marked as discount items. Coupon cannot be applied.");
            }
        } catch (error) {
            console.error("Error during discount check", error);
            return _t("Error checking product discount status.");
        }
        const rule = this.models["loyalty.rule"].find((rule) => {
            return rule.mode === "with_code" && (rule.promo_barcode === code || rule.code === code);
        });
        let claimableRewards = null;
        let coupon = null;
        if (rule) {
            const date_order = DateTime.fromSQL(order.date_order);

            if (
                rule.program_id.date_from &&
                date_order < rule.program_id.date_from
            ) {
                return _t("That promo code program is not yet valid.");
            }
            if (rule.program_id.date_to && date_order > rule.program_id.date_to) {
                return _t("That promo code program is expired.");
            }
            const program_pricelists = rule.program_id.pricelist_ids;
            if (
                program_pricelists.length > 0 &&
                (!order.pricelist_id ||
                    !program_pricelists.some((pr) => pr.id === order.pricelist_id.id))
            ) {
                return _t("That promo code program requires a specific pricelist.");
            }
            if (order.uiState.codeActivatedProgramRules.includes(rule.id)) {
                return _t("That promo code program has already been activated.");
            }
            order.uiState.codeActivatedProgramRules.push(rule.id);
            await this.orderUpdateLoyaltyPrograms();
            claimableRewards = order.getClaimableRewards(false, rule.program_id.id);
        } else {
            if (order._code_activated_coupon_ids.find((coupon) => coupon.code === code)) {
                return _t("That coupon code has already been scanned and activated.");
            }
            const customerId = order.get_partner() ? order.get_partner().id : false;
            const { successful, payload } = await this.data.call("pos.config", "use_coupon_code", [
                [this.config.id],
                code,
                order.date_order,
                customerId,
                order.pricelist_id ? order.pricelist_id.id : false,
            ]);
            if (successful) {
                // Allow rejecting a gift card that is not yet paid.

                const program = this.models["loyalty.program"].get(payload.program_id);
                if (program && program.program_type === "gift_card" && !payload.has_source_order) {
                    const confirmed = await ask(this.dialog, {
                        title: _t("Unpaid gift card"),
                        body: _t(
                            "This gift card is not linked to any order. Do you really want to apply its reward?"
                        ),
                    });
                    if (!confirmed) {
                        return _t("Unpaid gift card rejected.");
                    }
                }
                // TODO JCB: It's possible that the coupon is already loaded. We should check for that.
                //   - At the moment, creating a new one with existing id creates a duplicate.
                coupon = this.models["loyalty.card"].create({
                    id: payload.coupon_id,
                    code: code,
                    program_id: this.models["loyalty.program"].get(payload.program_id),
                    partner_id: this.models["res.partner"].get(payload.partner_id),
                    points: payload.points,
                    // TODO JCB: make the expiration_date work.
                    // expiration_date: payload.expiration_date,
                });
                order.update({ _code_activated_coupon_ids: [["link", coupon]] });
                await this.orderUpdateLoyaltyPrograms();
                claimableRewards = order.getClaimableRewards(coupon.id);
            } else {
                return payload.error_message;
            }
        }
        if (claimableRewards && claimableRewards.length === 1) {
            if (
                claimableRewards[0].reward.reward_type !== "product" ||
                !claimableRewards[0].reward.multi_product
            ) {
                order._applyReward(claimableRewards[0].reward, claimableRewards[0].coupon_id);
                this.updateRewards();
            }
        }
        if (!rule && order.lines.length === 0 && coupon) {
            return _t(
                "Gift Card: %s\nBalance: %s",
                code,
                this.env.utils.formatCurrency(coupon.points)
            );
        }
        return true;
    },


});