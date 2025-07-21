# -*- coding: utf-8 -*-
from odoo import http,fields
from odoo.http import request
from datetime import datetime

class PosDiscountController(http.Controller):

    @http.route('/pos/discount_rule', type='json', auth='public')
    def get_discount_rule(self, product_id, qty, pos_config_id=None):
        current_dt = fields.Datetime.now()
        company_id = request.env.company.id
        product = request.env['product.product'].sudo().browse(product_id)

        # First try to get category-based config
        category_ids = product.pos_categ_ids.ids if product.pos_categ_ids else []

        valid_config = request.env['discount.config'].sudo().search([
            ('discount_apply_on', '=', 'category'),
            ('start_date', '<=', current_dt),
            ('end_date', '>=', current_dt),
            ('company_id', '=', company_id),
            ('pos_config_ids', 'in', [pos_config_id]),
            ('categ_ids', 'in', category_ids),
        ], limit=1)

        # If not found, try product-based config
        if not valid_config:
            valid_config = request.env['discount.config'].sudo().search([
                ('discount_apply_on', '=', 'product'),
                ('product_id', '=', product_id),
                ('start_date', '<=', current_dt),
                ('end_date', '>=', current_dt),
                ('company_id', '=', company_id),
                ('pos_config_ids', 'in', [pos_config_id])
            ], limit=1)

        if not valid_config:
            return {}

        rules = request.env['discount.config.line'].sudo().search([
            ('config_id', '=', valid_config.id)
        ], order='from_quantity desc')

        discount_product_id = valid_config.discount_product.id
        blocks = []

        for rule in rules:
            max_qty = rule.to_quantity if rule.to_quantity > 0 else rule.from_quantity
            blocks.append({
                'min_qty': rule.from_quantity,
                'max_qty': max_qty,
                'discount': rule.discount_amount,
            })

        dp = [0] * (qty + 1)
        backtrack = [[] for _ in range(qty + 1)]

        for i in range(1, qty + 1):
            for block in blocks:
                for block_qty in range(block['min_qty'], block['max_qty'] + 1):
                    if block_qty <= i:
                        possible_discount = dp[i - block_qty] + block['discount']
                        if possible_discount > dp[i]:
                            dp[i] = possible_discount
                            backtrack[i] = backtrack[i - block_qty] + [(block_qty, block['discount'])]

        return {
            'qty': qty,
            'discount': dp[qty],
            'discount_product': discount_product_id,
            'split': backtrack[qty],
        }
