from odoo import models, fields,api
from datetime import timedelta
from odoo.exceptions import ValidationError
from datetime import datetime



class POSShopReportWizard(models.TransientModel):
    _name = 'pos.shop.report.wizard'
    _description = 'POS Shop Report Wizard'

    shop_id = fields.Many2one('pos.config', string='Shop', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    report_lines = fields.Json(string='Report Lines', readonly=True)
    payment_breakdown = fields.Json(string='Payment Breakdown', readonly=True)
    coupon_discount_total = fields.Float(string="Deducted Coupon", readonly=True)
    company_name = fields.Char(string="Company", compute="_compute_company_name")

    shop_address = fields.Char(string="Shop Address", compute="_compute_shop_contact")
    shop_phone = fields.Char(string="Shop Phone", compute="_compute_shop_contact")

    @api.depends('shop_id')
    def _compute_shop_contact(self):
        for wizard in self:
            warehouse = self.env['stock.warehouse'].search([('name', '=', wizard.shop_id.name)], limit=1)
            if warehouse and warehouse.partner_id:
                partner = warehouse.partner_id
                address_parts = [
                    partner.street or '',
                    partner.street2 or '',
                    partner.city or '',
                    partner.state_id.name if partner.state_id else '',
                    partner.zip or '',
                    partner.country_id.name if partner.country_id else ''
                ]
                wizard.shop_address = ', '.join([part for part in address_parts if part])
                wizard.shop_phone = partner.phone or ''
            else:
                wizard.shop_address = ''
                wizard.shop_phone = ''

    @api.depends('shop_id')
    def _compute_company_name(self):
        for wizard in self:
            wizard.company_name = wizard.shop_id.company_id.name if wizard.shop_id.company_id else self.env.company.name

    @api.onchange('date_end')
    def _check_date_range(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError("End Date cannot be earlier than Start Date.")

    def generate_report(self):
        self.ensure_one()
        self.report_lines = self._compute_report_lines()
        self.payment_breakdown = self._compute_payment_breakdown()
        self.coupon_discount_total = self._compute_coupon_discount()
        return self.env.ref('pos_shop_report.action_pos_shop_report').report_action(self)

    def _compute_report_lines(self):
        PosLine = self.env['pos.order.line']
        StockMove = self.env['stock.move']
        StockScrap = self.env['stock.scrap']

        lines = PosLine.search([
            ('order_id.config_id', '=', self.shop_id.id),
            ('order_id.date_order', '>=', self.date_start),
            ('order_id.date_order', '<=', self.date_end),
        ])

        if not lines:
            raise ValidationError("No record Found.")

        result = {}

        for line in lines.filtered(lambda l: l.price_subtotal_incl >= 0):
            product = line.product_id
            key = product.id
            if key not in result:
                result[key] = {
                    'sku': product.default_code or '',
                    'name': product.name or '',
                    'previous_stock': 0,
                    'stock_in': 0,
                    'scrap_qty': 0,
                    'sales_qty': 0,
                    'sales_refund_qty': 0,
                    'total_qty_today': 0,
                    'sales_amount': 0,
                    'discount_amount': 0,
                    'final_amount':0,
                }

            res = result[key]
            qty = line.qty
            price = line.price_unit
            discount = (price * qty) * (line.discount / 100)

            if qty > 0:
                res['sales_qty'] += qty
            else:
                res['sales_refund_qty'] += abs(qty)

            res['sales_amount'] += qty * price
            res['discount_amount'] += abs(discount)

        for product_id in result:
            product = self.env['product.product'].browse(product_id)

            stock_qty = product.with_context(to_date=self.date_start - timedelta(days=1)).qty_available
            result[product_id]['previous_stock'] = stock_qty

            incoming = StockMove.search([
                ('product_id', '=', product_id),
                ('date', '>=', self.date_start),
                ('date', '<=', self.date_end),
                ('state', '=', 'done'),
            ])
            result[product_id]['stock_in'] = sum(incoming.mapped('product_uom_qty'))

            scraps = StockScrap.search([
                ('product_id', '=', product_id),
                ('date_done', '>=', self.date_start),
                ('date_done', '<=', self.date_end),
                ('state', '=', 'done'),
            ])
            result[product_id]['scrap_qty'] = sum(scraps.mapped('scrap_qty'))

            res = result[product_id]
            res['total_qty_today'] =  res['sales_qty'] + res['sales_refund_qty']
            res['final_amount'] = res['sales_amount'] - res['discount_amount']

        return list(result.values())
    

    def _compute_payment_breakdown(self):
        Payment = self.env['pos.payment']
        orders = self.env['pos.order'].search([
            ('config_id', '=', self.shop_id.id),
            ('date_order', '>=', self.date_start),
            ('date_order', '<=', self.date_end),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ])
        payments = Payment.search([('pos_order_id', 'in', orders.ids)])
        
        breakdown = {}
        for payment in payments:
            name = payment.payment_method_id.name
            breakdown[name] = breakdown.get(name, 0.0) + payment.amount
        return breakdown

    def _compute_coupon_discount(self):
        PosLine = self.env['pos.order.line']
        lines = PosLine.search([
            ('order_id.config_id', '=', self.shop_id.id),
            ('order_id.date_order', '>=', self.date_start),
            ('order_id.date_order', '<=', self.date_end),
        ])
        discounted_lines = lines.filtered(lambda l: l.price_subtotal_incl < 0 and l.qty >= 0)

        return abs(sum(discounted_lines.mapped('price_subtotal_incl')))

