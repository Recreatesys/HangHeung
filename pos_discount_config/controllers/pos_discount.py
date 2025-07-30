# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class PosDiscountController(http.Controller):

    @http.route('/pos/discount_rule', type='json', auth='public')
    def get_discount_rule(self, product_qty_map, pos_config_id=None):
        current_dt = fields.Datetime.now()
        company_id = request.env.company.id
        all_discounts = []
        excluded_product_ids = set()
        product_ids = list(map(int, product_qty_map.keys()))

        product_configs = request.env['discount.config'].sudo().search([
            ('product_id', 'in', product_ids),
            ('start_date', '<=', current_dt),
            ('end_date', '>=', current_dt),
            ('company_id', '=', company_id),
            ('pos_config_ids', 'in', [pos_config_id]),
        ])

        config_map = defaultdict(lambda: {'config': None, 'product_ids': [], 'qty': 0})

        for config in product_configs:
            for product in config.product_id:
                pid = product.id
                qty = product_qty_map.get(str(pid), 0)
                if qty <= 0:
                    continue
                cid = config.id
                config_map[cid]['config'] = config
                config_map[cid]['product_ids'].append(pid)
                config_map[cid]['qty'] += qty

        for entry in config_map.values():
            if entry['qty'] <= 0:
                continue
            discount_info = self._apply_discount_rule(entry['product_ids'], entry['qty'], entry['config'])
            if discount_info:
                all_discounts.append(discount_info)
                excluded_product_ids.update(entry['product_ids'])

        global_bogo = request.env['discount.config'].sudo().search([
            ('product_id', '=', False),
            ('is_bogo', '=', True),
            ('start_date', '<=', current_dt),
            ('end_date', '>=', current_dt),
            ('company_id', '=', company_id),
            ('pos_config_ids', 'in', [pos_config_id])
        ], limit=1)

        if global_bogo:
            for pid, qty in product_qty_map.items():
                pid = int(pid)
                if pid in excluded_product_ids:
                    continue
                discount_info = self._apply_discount_rule([pid], qty, global_bogo)
                if discount_info:
                    all_discounts.append(discount_info)
                    excluded_product_ids.add(pid)

        global_bundle = request.env['discount.config'].sudo().search([
            ('product_id', '=', False),
            ('is_bogo', '=', False),
            ('start_date', '<=', current_dt),
            ('end_date', '>=', current_dt),
            ('company_id', '=', company_id),
            ('pos_config_ids', 'in', [pos_config_id])
        ], limit=1)

        if global_bundle:
            rules = request.env['discount.config.line'].sudo().search([
                ('config_id', '=', global_bundle.id)
            ], order='to_quantity desc')

            total_qty = 0
            included_pids = []

            for pid, qty in product_qty_map.items():
                pid = int(pid)
                if pid in excluded_product_ids:
                    continue
                total_qty += qty
                included_pids.append(pid)

            if total_qty > 0:
                rule_list = sorted([
                    (r.to_quantity, r.discount_amount)
                    for r in rules if r.to_quantity > 0 and r.discount_amount > 0
                ], reverse=True)

                dp = [(-1, []) for _ in range(total_qty + 1)]
                dp[0] = (0, [])

                for i in range(total_qty + 1):
                    current_discount, current_split = dp[i]
                    if current_discount == -1:
                        continue
                    for r_qty, r_disc in rule_list:
                        new_qty = i + r_qty
                        if new_qty <= total_qty:
                            new_discount = current_discount + r_disc
                            if new_discount > dp[new_qty][0]:
                                dp[new_qty] = (new_discount, current_split + [(r_qty, r_disc)])

                best_discount, best_split = dp[total_qty]
                if best_discount > 0:
                    all_discounts.append({
                        'product_ids': included_pids,
                        'discount_product': global_bundle.discount_product.id,
                        'total_qty': total_qty,
                        'discount': best_discount,
                        'split': best_split,
                        'type': 'bundle',
                    })

        return {'discount_lines': all_discounts}

    def _apply_discount_rule(self, product_ids, qty, config):
        if not config or not config.discount_product or qty <= 0:
            return None

        discount_info = {
            'product_ids': product_ids,
            'discount_product': config.discount_product.id,
            'total_qty': qty,
            'discount': 0.0,
            'split': [],
            'type': 'bogo' if config.is_bogo else 'bundle',
        }

        if config.is_bogo and len(product_ids) == 1:
            pid = product_ids[0]
            product = request.env['product.product'].sudo().browse(pid)
            unit_price = product.lst_price
            free_items = qty // 2
            total_discount = free_items * unit_price
            if total_discount > 0:
                discount_info.update({
                    'discount': total_discount,
                    'split': [(2, unit_price)] * free_items,
                })
        else:
            rules = request.env['discount.config.line'].sudo().search([
                ('config_id', '=', config.id)
            ], order='to_quantity desc')

            rule_list = sorted([
                (r.to_quantity, r.discount_amount)
                for r in rules if r.to_quantity > 0 and r.discount_amount > 0
            ], reverse=True)

            dp = [(-1, []) for _ in range(qty + 1)]
            dp[0] = (0, [])

            for i in range(qty + 1):
                current_discount, current_split = dp[i]
                if current_discount == -1:
                    continue
                for r_qty, r_disc in rule_list:
                    new_qty = i + r_qty
                    if new_qty <= qty:
                        new_discount = current_discount + r_disc
                        if new_discount > dp[new_qty][0]:
                            dp[new_qty] = (new_discount, current_split + [(r_qty, r_disc)])

            best_discount, best_split = dp[qty]
            if best_discount > 0:
                discount_info.update({
                    'discount': best_discount,
                    'split': best_split,
                })

        return discount_info if discount_info['discount'] > 0 else None
