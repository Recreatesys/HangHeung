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


    @api.onchange('date_end')
    def _check_date_range(self):
        for record in self:
            if record.date_start and record.date_end and record.date_end < record.date_start:
                raise ValidationError("End Date cannot be earlier than Start Date.")

    def generate_report(self):
        self.ensure_one()
        self.report_lines = self._compute_report_lines()
        self.payment_breakdown = self._compute_payment_breakdown()
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

        for line in lines:
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

            # stock_qty = product.with_context(to_date=self.date_start - timedelta(days=1)).qty_available
            # result[product_id]['previous_stock'] = stock_qty
            previous_date = datetime.combine(self.date_start - timedelta(days=1), datetime.max.time())

            incoming_before = StockMove.search([
                ('product_id', '=', product_id),
                ('date', '<=', previous_date),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'internal'),
            ])

            outgoing_before = StockMove.search([
                ('product_id', '=', product_id),
                ('date', '<=', previous_date),
                ('state', '=', 'done'),
                ('location_id.usage', '=', 'internal'),
            ])
            stock_qty = sum(incoming_before.mapped('product_uom_qty')) - sum(outgoing_before.mapped('product_uom_qty'))
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
            breakdown[name] = breakdown.get(name)
        return breakdown
