/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

export async function applyDiscountLogic(order_id) {
    const order = order_id;
    if (!order) return;

    const productModel = order_id.models?.["product.product"];
    const allProducts = productModel?.getAll?.() || [];

    const lines = Array.from(order.get_orderlines() || []);
    const productQtyMap = {};
    const discountLines = lines.filter(l => l.note === "AUTO:discount");

    for (const line of lines) {
        const pid = line.product_id?.id;
        if (pid) {
            productQtyMap[pid] = (productQtyMap[pid] || 0) + line.get_quantity();
        }
    }

    for (const [product_id_str, qty] of Object.entries(productQtyMap)) {
        const product_id = parseInt(product_id_str);

        let discountData = {};

        try {
            discountData = await rpc('/pos/discount_rule', { product_id, qty });
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

        } else if (existingDiscountLine) {
            order.removeOrderline(existingDiscountLine);
        }
    }

    for (const dline of discountLines) {
        const pid = dline.product_id?.id;
        if (pid && !productQtyMap[pid]) {
            order.removeOrderline(dline);
        }
    }
}


