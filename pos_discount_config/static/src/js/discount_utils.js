/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

export async function applyDiscountLogic(order_id) {
    const order = order_id;
    if (!order) return;

    const productModel = order_id.models?.["product.product"];
    const allProducts = productModel?.getAll?.() || [];

    const lines = Array.from(order.get_orderlines() || []);
    const product_qty_map = {};
    const discountLines = lines.filter(l => l.note === "AUTO:discount");

    for (const line of lines) {
        const pid = line.product_id?.id;
        if (pid) {
            product_qty_map[pid] = (product_qty_map[pid] || 0) + line.get_quantity();
        }
    }

    let discountData = {};

    try {
        const pos_config_id = order_id?.config_id?.id;
        discountData = await rpc('/pos/discount_rule', { product_qty_map, pos_config_id });
    } catch (error) {
        console.error("Error fetching discount rule:", error);
    }

    const discountProduct = discountData?.discount_product
        ? allProducts.find(p => p.id === discountData.discount_product)
        : null;

    const existingDiscountLine = discountLines.find(
        l => discountProduct && l.product_id?.id === discountProduct.id
    );


    if (discountData?.discount > 0 && discountProduct) {

        let split_summary = "";
        if (Array.isArray(discountData.split)) {
            const qtyCountMap = {};
            for (const [qty] of discountData.split) {
                qtyCountMap[qty] = (qtyCountMap[qty] || 0) + 1;
            }
            split_summary = Object.entries(qtyCountMap)
                .map(([qty, count]) => `${qty}×${count}`)
                .join(', ');
        }
        if (!existingDiscountLine) {
            const newLine = order_id.models["pos.order.line"].create({
                product_id: discountProduct,
                qty: 1,
                price_unit: -discountData.discount,
                order_id: order,
                note: "AUTO:discount",
                customer_note: split_summary || false,
            });

        } else {
            if (existingDiscountLine.get_unit_price() !== -discountData.discount) {
            existingDiscountLine.set_unit_price(-discountData.discount);
                }
            existingDiscountLine.customer_note = split_summary || false;
        }

    } else if (discountLines != []) {
        for (const dline of discountLines) {
            order.removeOrderline(dline);
        }
    }

    for (const dline of discountLines) {
        const pid = dline.product_id?.id;
        if (pid && !product_qty_map[pid] && dline) {
            order.removeOrderline(dline);
        }
    }
}


