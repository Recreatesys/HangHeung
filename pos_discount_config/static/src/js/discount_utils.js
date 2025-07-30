/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

const discountUpdateLocks = new WeakMap();
const discountTimerMap = new WeakMap();


export function scheduleDiscountLogic(order) {
    if (!order) return;

    if (discountTimerMap.get(order)) {
        clearTimeout(discountTimerMap.get(order));
    }

    const timer = setTimeout(() => {
        applyDiscountLogic(order);
    }, 30);

    discountTimerMap.set(order, timer);
}


export async function applyDiscountLogic(order) {
    if (!order) return;

    const lockKey = order.uid || order;
    if (discountUpdateLocks.get(lockKey)) return;
    discountUpdateLocks.set(lockKey, true);

    try {
        const productModel = order.models?.["product.product"];
        const allProducts = productModel?.getAll?.() || [];

        await Promise.resolve();
        const lines = Array.from(order.get_orderlines() || []);

        const product_qty_map = {};
        for (const line of lines) {
            const pid = line.product_id?.id;
            const price_unit = line.get_unit_price();
            const note = (line.note || line.get_note?.() || "").trim().toLowerCase();

            if (!pid || note.includes("auto:discount") || price_unit < 0) continue;
            product_qty_map[pid] = (product_qty_map[pid] || 0) + line.get_quantity();
        }

        let discountData = {};
        try {
            const pos_config_id = order?.config_id?.id;
            discountData = await rpc('/pos/discount_rule', { product_qty_map, pos_config_id });
        } catch (error) {
            console.error("Error fetching discount rule:", error);
            return;
        }

        const discountLines = lines.filter(l => l.note === "AUTO:discount");
        for (const dline of discountLines) {
            order.removeOrderline(dline);
        }

        const discountBlocks = discountData?.discount_lines || [];
        for (const block of discountBlocks) {
            const discountProduct = allProducts.find(p => p.id === block.discount_product);
            if (!discountProduct) continue;

            let split_summary = "";
            if (Array.isArray(block.split)) {
                const qtyCountMap = {};
                for (const [qty] of block.split) {
                    qtyCountMap[qty] = (qtyCountMap[qty] || 0) + 1;
                }
                split_summary = Object.entries(qtyCountMap)
                    .map(([qty, count]) => `${qty}×${count}`)
                    .join(", ");
            }

            order.models["pos.order.line"].create({
                product_id: discountProduct,
                qty: 1,
                price_unit: -block.discount,
                order_id: order,
                note: "AUTO:discount",
                customer_note: split_summary || false,
            });
        }

    } finally {
        discountUpdateLocks.set(lockKey, false);
    }
}
