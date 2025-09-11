import {patch} from "@web/core/utils/patch";
import {PosStore} from "@point_of_sale/app/store/pos_store";
const {DateTime} = luxon;
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

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
        const rule = this.models["loyalty.rule"].find((r) =>
            r.mode === "with_code" && (r.promo_barcode === code || r.code === code)
        );

        let claimableRewards = null;
        let coupon = null;
        if (rule) {
            const date_order = DateTime.fromSQL(order.date_order);

            if (rule.program_id.date_from && date_order < rule.program_id.date_from) {
                return _t("That promo code program is not yet valid.");
            }
            if (rule.program_id.date_to && date_order > rule.program_id.date_to) {
                return _t("That promo code program is expired.");
            }

            const programPricelists = rule.program_id.pricelist_ids;
            if (
                programPricelists.length > 0 &&
                (!order.pricelist_id ||
                    !programPricelists.some((pr) => pr.id === order.pricelist_id.id))
            ) {
                return _t("That promo code program requires a specific pricelist.");
            }

            if (order.uiState.codeActivatedProgramRules.includes(rule.id)) {
                return _t("That promo code program has already been activated.");
            }

            order.uiState.codeActivatedProgramRules.push(rule.id);
            await this.orderUpdateLoyaltyPrograms();

            if (order.get_orderlines().length === 0) {
                try {
                    const discountData = await rpc("/pos/get_coupon_discount_data", {
                        coupon_id: false,
                        program_id: rule.program_id.id,
                    });

                    const discountProductIds = discountData?.discount_product_ids || [];
                    const discountAmounts = discountData?.discount_amounts || {};

                    for (let productId of discountProductIds) {
                        const discountProduct = this.models["product.product"].find(
                            (p) => p.id === productId
                        );
                        if (discountProduct) {
                        order.models["pos.order.line"].create({
                        product_id: discountProduct,
                        qty: 1,
                        price_unit: discountAmounts[productId] || 0,
                        order_id: order,
                    });
                        }
                    }
                } catch (error) {
                    console.warn("Failed to fetch discount product(s) for program:", error);
                }
                await this.orderUpdateLoyaltyPrograms();
            }
            claimableRewards = order.getClaimableRewards(false, rule.program_id.id);

        } else {
            if (order._code_activated_coupon_ids.find((c) => c.code === code)) {
                return _t("That coupon code has already been scanned and activated.");
            }

            const customerId = order.get_partner() ? order.get_partner().id : false;
            const { successful, payload } = await rpc("/pos/use_coupon_code", {
                config_id: this.config.id,
                code,
                date_order: order.date_order,
                customer_id: customerId,
                pricelist_id: order.pricelist_id ? order.pricelist_id.id : false,
            });

            if (!successful) {
                return payload.error_message;
            }

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

            coupon = this.models["loyalty.card"].create({
                id: payload.coupon_id,
                code: code,
                program_id: program,
                partner_id: this.models["res.partner"].get(payload.partner_id),
                points: payload.points,
            });

            order.update({ _code_activated_coupon_ids: [["link", coupon]] });
            await this.orderUpdateLoyaltyPrograms();
            if (order.get_orderlines().length === 0) {
                try {
                    const discountData = await rpc("/pos/get_coupon_discount_data", {
                        coupon_id: payload.coupon_id,
                        program_id: payload.program_id,
                    });

                    const discountProductIds = discountData?.discount_product_ids || [];
                    const discountAmounts = discountData?.discount_amounts || {};

                    for (let productId of discountProductIds) {
                        const discountProduct = this.models["product.product"].find(
                            (p) => p.id === productId
                        );
                        if (discountProduct) {
                        order.models["pos.order.line"].create({
                        product_id: discountProduct,
                        qty: 1,
                        price_unit: discountAmounts[productId] || 0,
                        order_id: order,
                    });
                        }
                    }
                } catch (error) {
                    console.warn("Failed to fetch discount product(s) for coupon:", error);
                }
                await this.orderUpdateLoyaltyPrograms();
            }

            claimableRewards = order.getClaimableRewards(coupon.id);
        }

        // Apply rewards if available
        if (claimableRewards?.length) {
            const reward = claimableRewards[0].reward;
            if (reward.reward_type !== "product" || !reward.multi_product) {
                order._applyReward(reward, claimableRewards[0].coupon_id);
                this.updateRewards();
            }
        }

        // Display gift card balance if no lines and coupon used
        if (!rule && order.get_orderlines().length === 0 && coupon) {
            return _t(
                "Gift Card: %s\nBalance: %s",
                code,
                this.env.utils.formatCurrency(coupon.points)
            );
        }
        return true;
    },


});

patch(PosOrder.prototype, {
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
                        reward.reward_identifier_code === claimedReward.reward_identifier_code
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