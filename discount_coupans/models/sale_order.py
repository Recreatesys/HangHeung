from odoo import models, fields, api, _
from collections import defaultdict
from functools import partial
from datetime import datetime
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        order = super().create(vals)

        order_lines_data = vals.get('order_line', [])
        for command in order_lines_data:
            if command[0] in (0, 1):
                line_data = command[2]
                if not line_data:
                    continue

                product = self.env['product.product'].browse(line_data['product_id'])
                qty = line_data.get('product_uom_qty', 1)

                if product.is_coupon and product.loyalty_program_id:
                    order._generate_coupons_for_product(product, qty)

        return order

    def _generate_coupons_for_product(self, product, quantity):
        LoyaltyCard = self.env['loyalty.card']
        Lot = self.env['stock.lot']
        static_prefix = "CPN"

        last_card = LoyaltyCard.search([('prefix', '=', static_prefix)], order="id desc", limit=1)
        last_number = 0
        if last_card and last_card.code:
            try:
                last_number = int(last_card.code.replace(static_prefix, ''))
            except:
                pass

        for i in range(1, int(quantity) + 1):
            number = str(last_number + i).zfill(6)
            code = f"{static_prefix}{number}"


            lot = Lot.create({
                'name': code,
                'product_id': product.id,
            })
            warehouse = product.store_id.picking_type_id.warehouse_id
            location = warehouse.lot_stock_id or self.env.ref('stock.stock_location_stock')
            self.env['stock.quant'].create({
                'product_id': product.id,
                'location_id': location.id,
                'quantity': 1,
                'lot_id': lot.id,
            })


            pos_config = self.env['pos.config'].search([('company_id', '=', self.company_id.id)], limit=1)

            LoyaltyCard.create({
                'prefix': static_prefix,
                'range_from': number,
                'range_to': number,
                # 'store_id': product.store_id.id if product.store_id else (pos_config.id if pos_config else None),
                'allocated_store_id': product.store_id.id if product.store_id else (pos_config.id if pos_config else None),
                'code': code,
                'status': 'not_activated',
                'program_id': product.loyalty_program_id.id,
                'lot_id': lot.id,
            })

        self.message_post(body=f"{int(quantity)} coupons generated for product {product.display_name}.")

    def _add_loyalty_history_lines(self):
        self.ensure_one()
        points_per_coupon = defaultdict(partial(defaultdict, int))

        for coupon_point in self.coupon_point_ids:
            points_per_coupon[coupon_point.coupon_id]['issued'] = coupon_point.points

        for line in self.order_line:
            if not line.coupon_id:
                continue
            points_per_coupon[line.coupon_id]['cost'] += line.points_cost

        create_values = []
        base_values = {
            'order_id': self.id,
            'order_model': self._name,
            'description': _("Order %s", self.display_name),
            'salesperson_id': self.user_id.id,
        }

        for coupon, point_dict in points_per_coupon.items():
            cost = point_dict.get('cost', 0.0)
            issued = point_dict.get('issued', 0.0)
            create_values.append({
                **base_values,
                'card_id': coupon.id,
                'used': cost,
                'issued': issued,
            })

        self.env['loyalty.history'].create(create_values)

    def action_confirm(self):
        res = super().action_confirm()

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


class SaleLoyaltyCouponWizard(models.TransientModel):
    _inherit = 'sale.loyalty.coupon.wizard'

    def action_apply(self):
        self.ensure_one()
        res = super().action_apply()
        if self.coupon_code:
            coupon_id = self.env["loyalty.card"].search([('code', '=', self.coupon_code)], limit=1)
            if coupon_id and coupon_id.partner_id and coupon_id.partner_id.id != self.order_id.partner_id.id:
                raise ValidationError("This coupon is not valid for the selected customer")
        return res
