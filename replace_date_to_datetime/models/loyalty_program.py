import http
from odoo.exceptions import UserError
from odoo import api, fields, models, _
from odoo import http
from odoo.http import request

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    date_from = fields.Datetime(
        string="Start Date",
        help="The start date is included in the validity period of this program",
    )
    date_to = fields.Datetime(
        string="End date",
        help="The end date is included in the validity period of this program",
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_from_date_to(self):
        if any(p.date_to and p.date_from and fields.Date.to_date(p.date_from) > fields.Date.to_date(p.date_to) for p in self):
            raise UserError(_(
                "The validity period's start date must be anterior or equal to its end date."
            ))


class POSCouponDiscountController(http.Controller):
    @http.route('/pos/get_coupon_discount_data', type='json', auth='user')
    def get_coupon_discount_data(self, coupon_id, program_id, pricelist_id=False, partner_id=False):
        discount_product_ids = []
        discount_amounts = {}

        coupon = request.env['loyalty.card'].sudo().browse(coupon_id) if coupon_id else None
        program = None

        if coupon and coupon.exists():
            program = coupon.program_id
        elif program_id:
            program = request.env['loyalty.program'].sudo().browse(program_id)

        pricelist = (
            request.env['product.pricelist'].sudo().browse(pricelist_id)
            if pricelist_id else request.env['product.pricelist']
        )
        partner = (
            request.env['res.partner'].sudo().browse(partner_id)
            if partner_id else request.env['res.partner']
        )

        def _price_for(product):
            if pricelist:
                return pricelist._get_product_price(product, 1.0, partner=partner)
            return product.list_price

        if program and program.rule_ids:
            last_rule = program.rule_ids.sorted(key=lambda r: r.create_date)[-1]

            if last_rule.product_ids:
                for product in last_rule.product_ids:
                    discount_product_ids.append(product.id)
                    discount_amounts[product.id] = _price_for(product)
            else:
                all_products = request.env['product.product'].sudo().search([])
                for product in all_products:
                    discount_product_ids.append(product.id)
                    discount_amounts[product.id] = _price_for(product)

        return {
            'discount_product_ids': discount_product_ids,
            'discount_amounts': discount_amounts
        }

    @http.route('/pos/use_coupon_code', type='json', auth='user')
    def use_coupon_code(self, config_id, code, date_order, customer_id=False, pricelist_id=False):
        result = request.env['pos.config'].browse(config_id).use_coupon_code(
            code, date_order, customer_id, pricelist_id
        )
        return result