# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class PosDiscountController(http.Controller):

    @http.route('/pos/discount_rule', type='json', auth='public')
    def get_discount_rule(self, product_id, qty):
        rules = request.env['discount.config.line'].sudo().search([('config_id.product_id', '=', product_id)], order='from_quantity desc')

        config = request.env['discount.config'].sudo().search([('product_id', '=', product_id)])
        discount_product_id = config.discount_product.id

        blocks = []
        if rules:
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
        else:
            return {}
