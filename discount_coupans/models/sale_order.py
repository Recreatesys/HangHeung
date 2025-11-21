from odoo import models, fields, api, _
from collections import defaultdict
from functools import partial
from datetime import datetime
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        self.ensure_one()

        coupon_products = self.order_line.filtered(
            lambda l: l.product_id.is_coupon and l.product_id.loyalty_program_id
        ).mapped('product_id')

        if not coupon_products:
            return super().action_confirm()

        return {
            'name': "Generate Coupons",
            'type': 'ir.actions.act_window',
            'res_model': 'generate.coupon.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            }
        }

    def final_confirm_after_coupon(self):
        res = super(SaleOrder, self).action_confirm()

        for order in self:
            coupons = order.order_line.mapped('coupon_id')

            for coupon in coupons:
                status = 'activated'
                if int(coupon.points_display[0]) == 0:
                    status = 'redeemed'

                coupon.write({
                    'status': status,
                    'date_activation': fields.Datetime.now(),
                    'date_sale': fields.Datetime.now(),
                })

        return res

