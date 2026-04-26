import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cards = env['loyalty.card'].sudo().search([
        ('status', 'in', ('activated', 'redeemed')),
        ('sold_at_amount', '=', 0.0),
        ('code', '!=', False),
    ])
    if not cards:
        _logger.info("Coupon sold_at backfill: nothing to do.")
        return

    pos_pack_lot = env['pos.pack.operation.lot'].sudo()
    sale_line = env['sale.order.line'].sudo()

    backfilled_pos = 0
    backfilled_so = 0

    for card in cards:
        sold_at = None

        pack = pos_pack_lot.search([('lot_name', '=', card.code)], order='id desc', limit=1)
        line = pack.pos_order_line_id
        if line and line.qty:
            sold_at = line.price_subtotal_incl / line.qty
            backfilled_pos += 1
        else:
            so_lines = sale_line.search([('reserved_coupon_ids', 'in', card.id)], limit=1)
            if so_lines and so_lines.product_uom_qty:
                sold_at = so_lines.price_subtotal / so_lines.product_uom_qty
                backfilled_so += 1

        if sold_at is not None:
            card.write({'sold_at_amount': sold_at})

    _logger.info(
        "Coupon sold_at backfill: examined %d cards; backfilled %d from POS, %d from SO",
        len(cards), backfilled_pos, backfilled_so,
    )
