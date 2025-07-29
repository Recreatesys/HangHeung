# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import logging

logger = logging.getLogger(__name__)

class PosDiscountController(http.Controller):

    @http.route('/pos/discount_rule', type='json', auth='public')
    def get_discount_rule(self, product_qty_map, pos_config_id=None):
        """
        Apply discount once for total qty of all configured products combined.
        Priority: Product-specific > Global (all products).
        """
        current_dt = fields.Datetime.now()
        company_id = request.env.company.id
        product_ids = list(map(int, product_qty_map.keys()))

        # Step 1: Try product-specific config
        product_specific_config = request.env['discount.config'].sudo().search([
            ('product_id', 'in', product_ids),
            ('start_date', '<=', current_dt),
            ('end_date', '>=', current_dt),
            ('company_id', '=', company_id),
            ('pos_config_ids', 'in', [pos_config_id])
        ], limit=1)

        # Step 2: Fallback to global config
        if product_specific_config:
            valid_config = product_specific_config
        else:
            global_valid_config = request.env['discount.config'].sudo().search([
                ('product_id', '=', False),
                ('start_date', '<=', current_dt),
                ('end_date', '>=', current_dt),
                ('company_id', '=', company_id),
                ('pos_config_ids', 'in', [pos_config_id])
            ], limit=1)
            valid_config = global_valid_config

        if not valid_config:
            return {}

        # Step 3: Fetch rules
        rules = request.env['discount.config.line'].sudo().search([
            ('config_id', '=', valid_config.id)
        ], order='to_quantity desc')

        apply_to_all_products = not valid_config.product_id
        config_product_ids = valid_config.product_id.ids if valid_config.product_id else []

        # Step 4: Calculate total applicable quantity with logging
        total_qty = 0
        included_products = []

        for pid, qty in product_qty_map.items():
            if apply_to_all_products or int(pid) in config_product_ids:
                total_qty += qty
                included_products.append((int(pid), qty))

        logger.info(f" Discount rule applies to products: {included_products} → Total Qty: {total_qty}")

        if total_qty == 0:
            return {}

        if valid_config.is_bogo:
            discount_unit_price = 0.0
            for pid in product_ids:
                if apply_to_all_products or int(pid) in config_product_ids:
                    product = request.env['product.product'].sudo().browse(int(pid))
                    discount_unit_price = product.lst_price
                    break

            free_items = total_qty // 2
            total_discount = free_items * discount_unit_price
            logger.info(f"BOGO Applied: Qty={total_qty}, Free={free_items}, Discount={total_discount}")

            return {
                'total_qty': total_qty,
                'discount': total_discount,
                'discount_product': valid_config.discount_product.id,
                'split': [(2, discount_unit_price)] * free_items,
                'apply_to_product': config_product_ids[0] if config_product_ids else included_products[0][0],
            }

        rule_list = sorted([
            (rule.to_quantity, rule.discount_amount)
            for rule in rules if rule.to_quantity > 0 and rule.discount_amount > 0
        ], reverse=True)

        from collections import defaultdict

        # dp[i] = (max_discount, bundle_split)
        dp = [(-1, []) for _ in range(total_qty + 1)]
        dp[0] = (0, [])

        for i in range(total_qty + 1):
            current_discount, current_split = dp[i]
            if current_discount == -1:
                continue
            for qty, discount in rule_list:
                new_qty = i + qty
                if new_qty <= total_qty:
                    new_discount = current_discount + discount
                    if new_discount > dp[new_qty][0]:
                        dp[new_qty] = (
                            new_discount,
                            current_split + [(qty, discount)]
                        )

        best_discount, best_split = dp[total_qty]

        if best_discount <= 0:
            return {}

        logger.info(f" Bundle Discount Applied: Qty={total_qty}, Discount={best_discount}, Split={best_split}")

        return {
            'total_qty': total_qty,
            'discount': best_discount,
            'discount_product': valid_config.discount_product.id,
            'split': best_split,
            'apply_to_products': [pid for pid, _ in included_products],
        }
