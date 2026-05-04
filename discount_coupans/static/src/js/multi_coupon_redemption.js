/** @odoo-module **/
/**
 * Allow multiple coupon codes from the SAME coupon-type program to each
 * claim their reward in one POS transaction.
 *
 * Core pos_loyalty's getClaimableRewards skips a reward if any existing
 * orderline already references that reward.id when the program is of type
 * 'coupons' -- which blocks the second coupon scan from earning anything.
 *
 * We override the method and tighten the duplicate guard to also match
 * coupon_id, so different coupons from the same program each get their
 * reward, while the same coupon code re-scanned is still rejected upstream
 * at scan time (pos_store.js: "That coupon code has already been scanned").
 *
 * Source: pos_loyalty/static/src/overrides/models/pos_order.js (Odoo 18.0)
 *         method getClaimableRewards
 */

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

// HH-DEBUG: temporary verbose logging while diagnosing why two coupons
// from the same coupons-type program collapse into a single reward line.
const HH_LOG = (...a) => console.log("[HH-COUPON]", ...a);

patch(PosOrder.prototype, {
    getClaimableRewards(coupon_id = false, program_id = false, auto = false) {
        HH_LOG("getClaimableRewards called", { coupon_id, program_id, auto, lines: this.lines.length });
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
                // HH-CUSTOM: tighten core's "skip if reward already applied"
                // guard for coupon-type programs to also require the SAME
                // coupon_id. This lets two distinct codes from one program
                // each yield their reward in a single order; the same code
                // re-scanned is still rejected at scan-time upstream.
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
                if (reward.is_global_discount && reward.discount <= globalDiscountPercent) {
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
                HH_LOG("  pushed reward", { reward_id: reward.id, coupon_id: couponProgram.coupon_id });
            }
        }
        HH_LOG("getClaimableRewards result", result.map(r => ({reward_id: r.reward.id, coupon_id: r.coupon_id})));
        return result;
    },

    /**
     * Override of replace_date_to_datetime's _updateRewardLines.
     * That patch deduplicates rewards by `reward_identifier_code` alone --
     * which collapses two coupons of the same program (same reward) into
     * one line, even though we want each scanned coupon to keep its own
     * reward orderline. Tighten the dedup to also match coupon_id.
     *
     * Logic mirrors the upstream method (HH replace_date_to_datetime
     * pos_store.js), with the dedup predicate extended.
     */
    _updateRewardLines() {
        HH_LOG("_updateRewardLines called", { lines: this.lines.length });
        if (!this.lines.length) {
            return;
        }
        const rewardLines = this._get_reward_lines();
        HH_LOG("  reward lines:", rewardLines.map(l => ({
            id: l.id,
            reward_id: l.reward_id?.id,
            coupon_id: l.coupon_id?.id || l.coupon_id,
            code: l.reward_identifier_code,
            qty: l.qty,
            price: l.price_unit,
        })));
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
                // HH-CUSTOM: also key dedup on coupon_id so two distinct
                // coupons from the same coupon program each keep their
                // own reward orderline.
                !otherRewards.some(
                    (reward) =>
                        reward.reward_identifier_code === claimedReward.reward_identifier_code &&
                        reward.coupon_id === claimedReward.coupon_id
                )
            ) {
                otherRewards.push(claimedReward);
                HH_LOG("    pushed to otherRewards", {code: claimedReward.reward_identifier_code, coupon: claimedReward.coupon_id});
            } else {
                HH_LOG("    DEDUP-SKIPPED in otherRewards", {code: claimedReward.reward_identifier_code, coupon: claimedReward.coupon_id});
            }
            line.delete();
        }
        HH_LOG("  after loop: otherRewards count =", otherRewards.length);

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

        HH_LOG("  allRewardsMerged", allRewardsMerged.map(r => ({reward: r.reward.id, coupon: r.coupon_id})));
        for (const claimedReward of allRewardsMerged) {
            if (
                !this._code_activated_coupon_ids.find(
                    (coupon) => coupon.id === claimedReward.coupon_id
                ) &&
                !this.uiState.couponPointChanges[claimedReward.coupon_id]
            ) {
                HH_LOG("    SKIP (coupon not in activated set)", claimedReward.coupon_id);
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
                HH_LOG("    SKIP (already-applied check) reward=", claimedReward.reward.id, "coupon=", claimedReward.coupon_id);
                continue;
            }

            HH_LOG("    APPLY reward=", claimedReward.reward.id, "coupon=", claimedReward.coupon_id);
            const r = this._applyReward(
                claimedReward.reward,
                claimedReward.coupon_id,
                claimedReward.args
            );
            HH_LOG("      _applyReward returned:", r === true ? "OK" : r);
        }
    },
});
