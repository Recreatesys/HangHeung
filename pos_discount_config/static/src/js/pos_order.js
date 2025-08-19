/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

function _newRandomRewardCode() {
    return (Math.random() + 1).toString(36).substring(3);
}

patch(PosOrder.prototype, {
    /**
     * Override _getDiscountableOnSpecific to customize discount logic.
     */
    _getDiscountableOnSpecific(reward) {

        const applicableProductIds = new Set(reward.all_discount_product_ids.map((p) => p.id));
        const linesToDiscount = [];
        const discountLinesPerReward = {};
        const orderLines = this.get_orderlines();

        const remainingAmountPerLine = {};

        for (const line of orderLines) {
            const product = line.get_product();
            if (
                !product ||
                product.is_discount ||
                !line.get_quantity() ||
                !line.price_unit ||
                line.price_unit < 0
            ) {
                continue; // Skip if not a valid line or discount product or negative price
            }

            remainingAmountPerLine[line.uuid] = line.get_price_with_tax();
            const product_id = line.combo_parent_id?.product_id.id || product.id;
            if (
                applicableProductIds.has(product_id) ||
                (line._reward_product_id && applicableProductIds.has(line._reward_product_id.id))
            ) {
                linesToDiscount.push(line);
            }

            else if (line.reward_id) {
                const lineReward = line.reward_id;
                const lineRewardApplicableProductsIds = new Set(
                    lineReward.all_discount_product_ids.map((p) => p.id)
                );

                if (
                    lineReward.id === reward.id ||
                    (
                        lineReward.reward_type === "discount" &&
                        lineReward.discount_mode !== "percent" &&
                        lineRewardApplicableProductsIds.has(product_id) &&
                        applicableProductIds.has(product_id)
                    )
                ) {
                    linesToDiscount.push(line);
                }

                if (!discountLinesPerReward[line.reward_identifier_code]) {
                    discountLinesPerReward[line.reward_identifier_code] = [];
                }
                discountLinesPerReward[line.reward_identifier_code].push(line);
            }
        }

        let cheapestLine = false;
        for (const lines of Object.values(discountLinesPerReward)) {
            const lineReward = lines[0].reward_id;
            if (lineReward.reward_type !== "discount") {
                continue;
            }

            let discountedLines = orderLines.filter((line) => {
                const product = line.get_product();
                return product && product.is_discount === false;
            });

            if (lineReward.discount_applicability === "cheapest") {
                cheapestLine = cheapestLine || this._getCheapestLine();
                discountedLines = [cheapestLine].filter(l => l && l.get_product()?.is_discount === false);
            } else if (lineReward.discount_applicability === "specific") {
                discountedLines = this._getSpecificDiscountableLines(lineReward).filter(
                    l => l.get_product()?.is_discount === false
                );
            }

            if (!discountedLines.length) {
                continue;
            }

            if (lineReward.discount_mode === "percent") {
                const discount = lineReward.discount / 100;
                for (const line of discountedLines) {
                    if (line.reward_id) {
                        continue;
                    }
                    if (lineReward.discount_applicability === "cheapest") {
                        remainingAmountPerLine[line.uuid] *= 1 - discount / line.get_quantity();
                    } else {
                        remainingAmountPerLine[line.uuid] *= 1 - discount;
                    }
                }
            }
        }

        let discountable = 0;
        const discountablePerTax = {};
        for (const line of linesToDiscount) {
            discountable += remainingAmountPerLine[line.uuid];
            const taxKey = line.tax_ids.map((t) => t.id);
            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }
            discountablePerTax[taxKey] +=
                line.get_base_price() *
                (remainingAmountPerLine[line.uuid] / line.get_price_with_tax());
        }

        return { discountable, discountablePerTax };
    },


    _getCheapestLine() {
        const filtered_lines = this.get_orderlines().filter((line) => {
            const product = line.get_product();
            return (
                !line.comboParent &&
                !line.reward_id &&
                line.get_quantity &&
                product?.is_discount === false &&
                line.price_unit >= 0
            );
        });

        return filtered_lines.toSorted(
            (lineA, lineB) => lineA.getComboTotalPrice() - lineB.getComboTotalPrice()
        )[0];
    },

    _getDiscountableOnCheapest(reward) {
        const cheapestLine = this._getCheapestLine();
        if (!cheapestLine) {
            return { discountable: 0, discountablePerTax: {} };
        }

        const product = cheapestLine.get_product();
        if (product?.is_discount || cheapestLine.price_unit < 0) {
            return { discountable: 0, discountablePerTax: {} };
        }

        const taxKey = cheapestLine.tax_ids.map((t) => t.id);
        const priceWithoutTax = cheapestLine.getComboTotalPriceWithoutTax();

        return {
            discountable: priceWithoutTax,
            discountablePerTax: {
                [taxKey]: priceWithoutTax,
            },
        };
    },
    _getDiscountableOnOrder(reward) {
        let discountable = 0;
        const discountablePerTax = {};

        for (const line of this.get_orderlines()) {
            const product = line.get_product();

            if (
                !line.get_quantity() ||
                !product ||
                product.is_discount ||
                line.price_unit < 0
            ) {
                continue;
            }

            const taxKey = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? line.tax_ids.map((t) => t.id)
                : line.tax_ids.filter((t) => t.amount_type !== "fixed").map((t) => t.id);

            discountable += line.get_price_with_tax();

            if (!discountablePerTax[taxKey]) {
                discountablePerTax[taxKey] = 0;
            }

            discountablePerTax[taxKey] += line.get_base_price();
        }

        return { discountable, discountablePerTax };
    },

    _getRewardLineValuesDiscount(args) {

        const reward = args["reward"];
        const coupon_id = args["coupon_id"];
        const rewardAppliesTo = reward.discount_applicability;
        let getDiscountable;
        if (rewardAppliesTo === "order") {
            getDiscountable = this._getDiscountableOnOrder.bind(this);
        } else if (rewardAppliesTo === "cheapest") {
            getDiscountable = this._getDiscountableOnCheapest.bind(this);
        } else if (rewardAppliesTo === "specific") {
            getDiscountable = this._getDiscountableOnSpecific.bind(this);
        }
        if (!getDiscountable) {
            return _t("Unknown discount type");
        }
        let { discountable, discountablePerTax } = getDiscountable(reward);
        discountable = Math.min(this.get_total_with_tax(), discountable);
        if (!discountable) {
            return [];
        }
        let maxDiscount = reward.discount_max_amount || Infinity;
        if (reward.discount_mode === "per_point") {
            const points = ["ewallet", "gift_card"].includes(reward.program_id.program_type)
                ? this._getRealCouponPoints(coupon_id)
                : Math.floor(this._getRealCouponPoints(coupon_id) / reward.required_points) *
                  reward.required_points;
            maxDiscount = Math.min(maxDiscount, reward.discount * points);
        } else if (reward.discount_mode === "per_order") {
            maxDiscount = Math.min(maxDiscount, reward.discount);
        } else if (reward.discount_mode === "percent") {
            maxDiscount = Math.min(maxDiscount, discountable * (reward.discount / 100));
        }
        const rewardCode = _newRandomRewardCode();
        let pointCost = reward.clear_wallet
            ? this._getRealCouponPoints(coupon_id)
            : reward.required_points;
        if (reward.discount_mode === "per_point" && !reward.clear_wallet) {
            pointCost = Math.min(maxDiscount, discountable) / reward.discount;
        }

        const discountProduct = reward.discount_line_product_id;
        if (["ewallet", "gift_card"].includes(reward.program_id.program_type)) {
            const new_price = compute_price_force_price_include(
                discountProduct.taxes_id,
                -Math.min(maxDiscount, discountable),
                discountProduct,
                this.config._product_default_values,
                this.company,
                this.currency,
                this.models
            );

            return [
                {
                    product_id: discountProduct,
                    price_unit: new_price,
                    qty: 1,
                    reward_id: reward,
                    is_reward_line: true,
                    coupon_id: coupon_id,
                    points_cost: pointCost,
                    reward_identifier_code: rewardCode,
                    tax_ids: discountProduct.taxes_id,
                },
            ];
        }
        const discountFactor = discountable ? Math.min(1, maxDiscount / discountable) : 1;
        const result = Object.entries(discountablePerTax).reduce((lst, entry) => {

            if (!entry[1]) {
                return lst;
            }
            let taxIds = entry[0] === "" ? [] : entry[0].split(",").map((str) => parseInt(str));
            taxIds = this.models["account.tax"].filter((tax) => taxIds.includes(tax.id));

            lst.push({
                product_id: discountProduct,
                price_unit: -(entry[1] * discountFactor),
                qty: 1,
                reward_id: reward,
                is_reward_line: true,
                coupon_id: coupon_id,
                points_cost: 0,
                reward_identifier_code: rewardCode,
                tax_ids: taxIds,
            });
            return lst;
        }, []);
        if (result.length) {
            result[0]["points_cost"] = pointCost;
        }
        return result;
    },

});