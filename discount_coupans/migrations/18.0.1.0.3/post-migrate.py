import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

NON_COUPON_PROGRAM_TYPES = ('promotion', 'promo_code', 'buy_x_get_y', 'next_order_coupons')

DUAL_USE_PRODUCT_ID = 2026  # CLP 九折 — used by both CLP Card (coupons) and many promotions


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    pos_discount_categ = env.ref(
        'discount_coupans.product_category_pos_discount',
        raise_if_not_found=False,
    )
    if not pos_discount_categ:
        _logger.warning("POS Discount category XML record not found; skipping migration.")
        return

    company_1 = env['res.company'].browse(1)
    pos_discount_account = env['account.account'].with_company(company_1).search([
        ('account_type', '=', 'income'),
        ('code', '=', '400010'),
    ], limit=1)
    if not pos_discount_account:
        pos_discount_account = env['account.account'].search([
            ('name', 'ilike', 'POS Discount'),
            ('account_type', '=', 'income'),
        ], limit=1)
    if not pos_discount_account:
        _logger.warning("Account 400010 POS Discount not found; category income mapping skipped.")
    else:
        income_map = dict(pos_discount_categ.property_account_income_categ_id or {})
        income_map['1'] = pos_discount_account.id
        pos_discount_categ.property_account_income_categ_id = income_map
        _logger.info(
            "POS Discount category %s mapped to account %s for company 1",
            pos_discount_categ.id, pos_discount_account.id,
        )

    dual_use = env['product.product'].browse(DUAL_USE_PRODUCT_ID).exists()
    dual_use_clone = env['product.product']
    if dual_use:
        promotion_rewards_using_dual = env['loyalty.reward'].search([
            ('discount_line_product_id', '=', dual_use.id),
            ('program_id.program_type', 'in', NON_COUPON_PROGRAM_TYPES),
        ])
        if promotion_rewards_using_dual:
            existing = env['product.product'].search([
                ('product_tmpl_id.name', '=', (dual_use.name or '') + ' (Promotion)'),
            ], limit=1)
            if existing:
                dual_use_clone = existing
            else:
                dual_use_clone = dual_use.copy({'name': (dual_use.name or '') + ' (Promotion)'})
            dual_use_clone.product_tmpl_id.categ_id = pos_discount_categ
            promotion_rewards_using_dual.write({'discount_line_product_id': dual_use_clone.id})
            _logger.info(
                "Dual-use product %s (id=%s): cloned to id=%s and re-pointed %d rewards",
                dual_use.name, dual_use.id, dual_use_clone.id, len(promotion_rewards_using_dual),
            )

    rewards = env['loyalty.reward'].search([
        ('program_id.program_type', 'in', NON_COUPON_PROGRAM_TYPES),
        ('program_id.active', '=', True),
        ('discount_line_product_id', '!=', False),
    ])
    loyalty_dlps = rewards.mapped('discount_line_product_id')

    discount_configs = env['discount.config'].search([])
    config_dlps = discount_configs.mapped('discount_product')

    in_scope = (loyalty_dlps | config_dlps) - dual_use
    to_move = in_scope.filtered(lambda p: p.categ_id != pos_discount_categ)

    moved = 0
    if to_move:
        templates_to_move = to_move.mapped('product_tmpl_id')
        templates_to_move = templates_to_move.filtered(lambda t: t.categ_id != pos_discount_categ)
        templates_to_move.write({'categ_id': pos_discount_categ.id})
        moved = len(templates_to_move)

    _logger.info(
        "POS Discount routing migration: %d in-scope products inspected, %d templates moved into category %s",
        len(in_scope), moved, pos_discount_categ.id,
    )
