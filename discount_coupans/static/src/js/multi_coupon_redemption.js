/** @odoo-module **/
/**
 * Allow multiple coupon codes from the SAME coupon-type program to each
 * claim their reward in one POS transaction.
 *
 * Core pos_loyalty enforces three anti-stacking guards that, in
 * combination, collapse two same-program coupon redemptions into one
 * line. We override each one for coupons-type programs only:
 *
 * 1. getClaimableRewards: skips a reward if any existing orderline
 *    references reward.id when program_type === 'coupons'. Tighten the
 *    duplicate guard to also require the SAME coupon_id, so different
 *    coupon codes from one program each get their reward.
 *
 * 2. getClaimableRewards: skips an is_global_discount reward if its
 *    discount value is <= an already-applied global-discount line.
 *    This is the "best-of-N percent discounts" rule and is wrong for
 *    fixed-amount cash coupons -- bypass it for coupons-type programs.
 *
 * 3. _applyReward: deletes existing global-discount lines before adding
 *    a new is_global_discount reward. Same wrong assumption as (2).
 *    Skip the deletion when the new reward is from a coupons-type
 *    program.
 *
 * Plus: replace_date_to_datetime's _updateRewardLines deduplicates
 * existing reward lines by reward_identifier_code alone -- collapses
 * two same-program coupons into one. Tighten the dedup to also match
 * coupon_id.
 */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    getClaimableRewards(coupon_id = false, program_id = false, auto = false) {
        const couponPointChanges = this.uiState.couponPointChanges;
        const excludedCouponIds = Object.keys(couponPointChanges)
            .filter((id) => couponPointChanges[id].manual && couponPointChanges[id].existing_code)
            .map((id) => couponPointChanges[id].coupon_id);

        const allCouponPrograms = Object.values(this.uiState.couponPointChanges)
            .filter((pe) => !excludedCouponIds.includes(pe.coupon_id))
            .map((pe) => ({
                program_id: pe.program_id,
                coupon_id: pe.coupon_id,
            }))
            .concat(
                this._code_activated_coupon_ids.map((coupon) => ({
                    program_id: coupon.program_id.id,
                    coupon_id: coupon.id,
                }))
            );
        const result = [];
        const totalWithTax = this.get_total_with_tax();
        const totalWithoutTax = this.get_total_without_tax();
        const totalIsZero = totalWithTax === 0;
        const globalDiscountLines = this._getGlobalDiscountLines();
        const globalDiscountPercent = globalDiscountLines.length
            ? globalDiscountLines[0].reward_id.discount
            : 0;
        for (const couponProgram of allCouponPrograms) {
            const program = this.models["loyalty.program"].get(couponProgram.program_id);
            if (
                program.pricelist_ids.length > 0 &&
                (!this.pricelist_id ||
                    !program.pricelist_ids.some((pl) => pl.id === this.pricelist_id.id))
            ) {
                continue;
            }
            if (program.trigger == "with_code") {
                if (!this._canGenerateRewards(program, totalWithTax, totalWithoutTax)) {
                    continue;
                }
            }
            if (
                (coupon_id && couponProgram.coupon_id !== coupon_id) ||
                (program_id && couponProgram.program_id !== program_id)
            ) {
                continue;
            }
            const points = this._getRealCouponPoints(couponProgram.coupon_id);
            for (const reward of program.reward_ids) {
                if (points < reward.required_points) {
                    continue;
                }
                // HH-CUSTOM (1): for coupons-type, only skip if THIS exact
                // coupon already has its reward applied -- not just any
                // coupon from the program.
                if (
                    reward.program_id.program_type === "coupons" &&
                    this.lines.find(
                        (rewardline) =>
                            rewardline.reward_id?.id === reward.id &&
                            rewardline.coupon_id?.id === couponProgram.coupon_id
                    )
                ) {
                    continue;
                }
                if (auto && this.uiState.disabledRewards.has(reward.id)) {
                    continue;
                }
                // HH-CUSTOM (2): bypass the "best-of-N global discount"
                // anti-stacking guard for coupons-type programs. Each
                // physical cash coupon must contribute its own reward
                // line regardless of an already-applied one.
                if (
                    reward.is_global_discount &&
                    reward.discount <= globalDiscountPercent &&
                    reward.program_id.program_type !== "coupons"
                ) {
                    continue;
                }
                if (reward.reward_type === "discount" && totalIsZero) {
                    continue;
                }
                let unclaimedQty;
                if (reward.reward_type === "product") {
                    if (!reward.multi_product) {
                        const product = reward.reward_product_id;
                        if (!product) {
                            continue;
                        }
                        unclaimedQty = this._computeUnclaimedFreeProductQty(
                            reward,
                            couponProgram.coupon_id,
                            product,
                            points
                        );
                    }
                    if (!unclaimedQty || unclaimedQty <= 0) {
                        continue;
                    }
                }
                result.push({
                    coupon_id: couponProgram.coupon_id,
                    reward: reward,
                    potentialQty: unclaimedQty,
                });
            }
        }
        return result;
    },

    /**
     * HH-CUSTOM (3): override _applyReward to skip core's "delete
     * existing global-discount lines before adding new one" behaviour
     * when the new reward is from a coupons-type program. Otherwise
     * applying coupon B wipes out coupon A's already-applied line.
     */
    _applyReward(reward, coupon_id, args) {
        if (
            reward.is_global_discount &&
            reward.program_id.program_type === "coupons"
        ) {
            // Inline a stripped-down version of core's _applyReward that
            // omits the global-discount-line deletion. Mirrors
            // pos_loyalty/static/src/overrides/models/pos_order.js
            // (Odoo 18.0).
            if (this._getRealCouponPoints(coupon_id) < reward.required_points) {
                return false;
            }
            args = args || {};
            const rewardLines = this._getRewardLineValues({
                reward: reward,
                coupon_id: coupon_id,
                product: args["product"] || null,
                price: args["price"] || null,
                quantity: args["quantity"] || null,
                cost: args["cost"] || null,
            });
            if (!Array.isArray(rewardLines)) {
                return rewardLines;
            }
            if (!rewardLines.length) {
                return false;
            }
            for (const rewardLine of rewardLines) {
                const prepareRewards = {
                    ...rewardLine,
                    reward_id: rewardLine.reward_id,
                    coupon_id: this.models["loyalty.card"].get(rewardLine.coupon_id),
                    tax_ids: rewardLine.tax_ids.map((tax) => ["link", tax]),
                };
                this.models["pos.order.line"].create({
                    ...prepareRewards,
                    order_id: this,
                    price_type: "manual",
                });
            }
            return true;
        }
        return super._applyReward(reward, coupon_id, args);
    },

    /**
     * Override of replace_date_to_datetime's _updateRewardLines.
     * That patch deduplicates rewards by reward_identifier_code alone --
     * which collapses two coupons of the same program into one line.
     * Tighten the dedup to also match coupon_id.
     */
    _updateRewardLines() {
        if (!this.lines.length) {
            return;
        }
        const rewardLines = this._get_reward_lines();
        if (!rewardLines.length) {
            return;
        }

        const productRewards = [];
        const otherRewards = [];
        const paymentRewards = [];

        for (const line of rewardLines) {
            const couponId = line.coupon_id?.id || line.coupon_id;
            const productId = line._reward_product_id?.id || line._reward_product_id;

            const claimedReward = {
                reward: line.reward_id,
                coupon_id: couponId,
                args: {
                    product: productId,
                    price: line.price_unit,
                    quantity: line.qty,
                    cost: line.points_cost,
                },
                reward_identifier_code: line.reward_identifier_code,
            };

            if (
                claimedReward.reward.program_id.program_type === "gift_card" ||
                claimedReward.reward.program_id.program_type === "ewallet"
            ) {
                paymentRewards.push(claimedReward);
            } else if (claimedReward.reward.reward_type === "product") {
                productRewards.push(claimedReward);
            } else if (
                !otherRewards.some(
                    (reward) =>
                        reward.reward_identifier_code === claimedReward.reward_identifier_code &&
                        reward.coupon_id === claimedReward.coupon_id
                )
            ) {
                otherRewards.push(claimedReward);
            }
            line.delete();
        }

        const allRewards = productRewards.concat(otherRewards).concat(paymentRewards);
        const allRewardsMerged = [];

        allRewards.forEach((reward) => {
            if (reward.reward.reward_type === "discount") {
                allRewardsMerged.push(reward);
                return;
            }
            const reward_index = allRewardsMerged.findIndex((item) => {
                return (
                    item.reward.id === reward.reward.id &&
                    item.args.price === reward.args.price &&
                    item.coupon_id === reward.coupon_id &&
                    item.args.product === reward.args.product
                );
            });
            if (reward_index > -1) {
                allRewardsMerged[reward_index].args.quantity += reward.args.quantity;
                allRewardsMerged[reward_index].args.cost += reward.args.cost;
            } else {
                allRewardsMerged.push(reward);
            }
        });

        for (const claimedReward of allRewardsMerged) {
            if (
                !this._code_activated_coupon_ids.find(
                    (coupon) => coupon.id === claimedReward.coupon_id
                ) &&
                !this.uiState.couponPointChanges[claimedReward.coupon_id]
            ) {
                continue;
            }
            if (
                claimedReward.reward.program_id.program_type === "coupons" &&
                this.lines.find(
                    (rewardline) =>
                        rewardline.reward_id?.id === claimedReward.reward.id &&
                        (rewardline.coupon_id?.id === claimedReward.coupon_id ||
                            rewardline.coupon_id === claimedReward.coupon_id)
                )
            ) {
                continue;
            }
            this._applyReward(
                claimedReward.reward,
                claimedReward.coupon_id,
                claimedReward.args
            );
        }
    },
});
