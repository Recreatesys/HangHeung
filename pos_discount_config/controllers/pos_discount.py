# -*- coding: utf-8 -*-
from odoo import http,fields
from odoo.http import request
from datetime import datetime

class PosDiscountController(http.Controller):

    @http.route('/pos/discount_rule', type='json', auth='public')
    def get_discount_rule(self, product_qty_map, pos_config_id=None):
        """
        Apply discount once for total qty of all configured products combined.
        Handles both 'product' and 'category' based discount configs.
        """
        current_dt = fields.Datetime.now()
        company_id = request.env.company.id
        product_ids = list(map(int, product_qty_map.keys()))

        products = request.env['product.product'].sudo().browse(product_ids)
        product_categ_map = {p.id: p.pos_categ_ids.ids for p in products}

        all_category_ids = list({cat_id for cat_list in product_categ_map.values() for cat_id in cat_list})
        valid_config = None

        if all_category_ids:
            valid_config = request.env['discount.config'].sudo().search([
                ('discount_apply_on', '=', 'category'),
                ('start_date', '<=', current_dt),
                ('end_date', '>=', current_dt),
                ('company_id', '=', company_id),
                ('pos_config_ids', 'in', [pos_config_id]),
                ('categ_ids', 'in', all_category_ids),
            ], limit=1)

        if not valid_config:
            valid_config = request.env['discount.config'].sudo().search([
                ('discount_apply_on', '=', 'product'),
                ('product_id', 'in', product_ids),
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

        total_qty = 0

        if valid_config.discount_apply_on == 'product':
            config_product_ids = valid_config.product_id.ids
            for pid, qty in product_qty_map.items():
                if int(pid) in config_product_ids:
                    total_qty += qty

        elif valid_config.discount_apply_on == 'category':
            config_categ_ids = valid_config.categ_ids.ids
            for pid, qty in product_qty_map.items():
                product_categs = product_categ_map.get(int(pid), [])
                if any(cid in config_categ_ids for cid in product_categs):
                    total_qty += qty

        if total_qty == 0:
            return {}

        applicable_rule = None
        for rule in rules:
            from_qty = rule.from_quantity
            to_qty = rule.to_quantity if rule.to_quantity > 0 else rule.from_quantity
            if from_qty <= total_qty <= to_qty:
                applicable_rule = rule
                break

        if not applicable_rule:
            last_rule = request.env['discount.config.line'].sudo().search([('config_id', '=', valid_config.id)], order='to_quantity desc', limit=1)
            min_from_qty = min(rules.mapped('from_quantity'))
            max_to_qty = min(rules.mapped('to_quantity'))
            if min_from_qty <= total_qty and max_to_qty <= total_qty:
                applicable_rule = last_rule

        return {
            'total_qty': total_qty,
            'discount': applicable_rule.discount_amount,
            'discount_product': valid_config.discount_product.id,
            'split': [(total_qty, applicable_rule.discount_amount)],
        }
