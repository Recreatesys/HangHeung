from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()

        for order in self:
            for line in order.order_line.filtered(
                lambda l: l.product_id.is_coupon and l.reserved_coupon_ids
            ):
                picking = order.picking_ids.filtered(
                    lambda p: p.state not in ('cancel')
                )[:1]

                if not picking:
                    continue

                picking.action_assign()

                move = picking.move_ids.filtered(
                    lambda m: m.product_id == line.product_id
                )[:1]

                if not move:
                    continue

                for coupon in line.reserved_coupon_ids:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': line.product_id.id,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': coupon.lot_id.id,
                        'qty_done': 1,
                    })
        return res

from odoo import models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    reserved_coupon_ids = fields.Many2many(
        'loyalty.card',
        string="Reserved Coupons",
        copy=False
    )

    def generate_coupon_button(self):
        self.ensure_one()
        return {
            'name': 'Generate / Sell Coupons',
            'type': 'ir.actions.act_window',
            'res_model': 'generate.coupon.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_line_id': self.id,
            }
        }
