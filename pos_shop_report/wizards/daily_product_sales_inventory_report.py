import io
import base64
import xlsxwriter
from datetime import timedelta
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DailyProductSalesInventoryReport(models.TransientModel):
    _name = 'daily.product.sales.inventory.report'
    _description = 'POS Daily Product Sales and Inventory Report'

    shop_id = fields.Many2one('pos.config', string='Shop', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    def _compute_report_lines(self):
        company = self.env.company
        PosLine = self.env['pos.order.line']
        StockMove = self.env['stock.move']
        StockScrap = self.env['stock.scrap']

        all_products = self.env['product.product'].search([
            ('type', 'in', ['product', 'consu', 'combo']),
        ])

        lines = PosLine.search([
            ('order_id.config_id', '=', self.shop_id.id),
            ('order_id.date_order', '>=', self.date_start),
            ('order_id.date_order', '<=', self.date_end),
            ('order_id.company_id', '=', company.id),
        ])

        result = {}

        for product in all_products:
            result[product.id] = {
                'product_id': product.id,
                'sku': product.default_code or '',
                'name': product.name or '',
                'unit': product.uom_id.name,
                'price': product.lst_price,
                'previous_stock': 0,
                'stock_in': 0,
                'scrap_qty': 0,
                'sales_qty': 0,
                'sales_refund_qty': 0,
                'total_qty_today': 0,
                'sales_amount': 0,
                'discount_amount': 0,
                'final_amount': 0,
            }

        for line in lines:
            product = line.product_id
            key = product.id

            if key not in result:
                result[key] = {
                    'product_id': product.id,
                    'sku': product.default_code or '',
                    'name': product.name or '',
                    'unit': product.uom_id.name,
                    'price': product.lst_price,
                    'previous_stock': 0,
                    'stock_in': 0,
                    'scrap_qty': 0,
                    'sales_qty': 0,
                    'sales_refund_qty': 0,
                    'total_qty_today': 0,
                    'sales_amount': 0,
                    'discount_amount': 0,
                    'final_amount': 0,
                }

            res = result[key]
            qty = line.qty
            price = line.price_unit
            discount = (price * qty) * (line.discount / 100)

            if qty > 0:
                res['sales_qty'] += qty
                res['sales_amount'] += qty * price
                res['discount_amount'] += discount
            else:
                res['sales_refund_qty'] += abs(qty)
                res['sales_amount'] -= abs(qty * price)
                res['discount_amount'] += discount


        for product_id in result:
            product = self.env['product.product'].browse(product_id)

            stock_qty = product.with_context(to_date=self.date_start - timedelta(days=1)).qty_available
            result[product_id]['previous_stock'] = stock_qty

            incoming = StockMove.search([
                ('product_id', '=', product_id),
                ('date', '>=', self.date_start),
                ('date', '<=', self.date_end),
                ('state', '=', 'done'),
                ('company_id', '=', company.id),
            ])
            result[product_id]['stock_in'] = sum(incoming.mapped('product_uom_qty'))

            scraps = StockScrap.search([
                ('product_id', '=', product_id),
                ('date_done', '>=', self.date_start),
                ('date_done', '<=', self.date_end),
                ('state', '=', 'done'),
                ('company_id', '=', company.id),
            ])
            result[product_id]['scrap_qty'] = sum(scraps.mapped('scrap_qty'))

            res = result[product_id]
            res['total_qty_today'] = res['sales_qty'] + res['sales_refund_qty']
            res['final_amount'] = res['sales_amount'] - res['discount_amount']

        return list(result.values())

    def generate_xls_report(self):
        company = self.env.company
        self.ensure_one()
        report_lines = self._compute_report_lines()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Daily Product Sales and Inventory Report')

        header_title = workbook.add_format({'bold': True, 'font_size': 14})
        header_label = workbook.add_format({'bold': True, 'font_size': 12})
        header_value = workbook.add_format({'font_size': 12})
        table_header = workbook.add_format({'bold': True, 'bg_color': '#CCCCCC', 'border': 1})
        normal_format = workbook.add_format({'border': 1})

        row = 0

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 35)
        sheet.set_column('C:N', 10)

        sheet.write(row, 0, company.name, header_title)
        row += 2

        sheet.write(row, 0, "當天貨品銷售及庫存報表", header_label)
        row += 2

        sheet.write(row, 0, "日期:", header_label)
        sheet.write(row, 1, f"{self.date_start} ~ {self.date_end}", header_value)
        row += 1

        sheet.write(row, 0, "分店:", header_label)
        sheet.write(row, 1, self.shop_id.name or '', header_value)
        row += 2

        headers = ['產品編號', '產品名稱', '單位', '價錢', '上存', '進貨數', '銷售數', '退貨數', '棄貨數', '調整數', '結存數', '銷售金額', '折扣金額', '銷售淨額']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, table_header)
        row += 1

        for line in report_lines:

            product = self.env['product.product'].browse(line.get('product_id'))

            adjustment_location = self.env['stock.location'].search([
                ('complete_name', '=', 'Virtual Locations/Inventory adjustment'),
                ('company_id', '=', company.id),
            ], limit=1)

            adjustment_quants = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', adjustment_location.id),
                ('company_id', '=', company.id),
            ])
            adjustment_qty = sum(adjustment_quants.mapped('quantity'))

            opening_stock = line.get('previous_stock', 0)
            stock_in = line.get('stock_in', 0)
            sales_qty = line.get('sales_qty', 0)
            sales_refund_qty = line.get('sales_refund_qty', 0)
            scrap_qty = line.get('scrap_qty', 0)

            closing_stock = opening_stock + stock_in - sales_qty + sales_refund_qty - scrap_qty + adjustment_qty

            sheet.write(row, 0, line.get('sku', ''), normal_format)
            sheet.write(row, 1, line.get('name', ''), normal_format)
            sheet.write(row, 2, line.get('unit', ''), normal_format)
            sheet.write(row, 3, line.get('price', 0.0), normal_format)
            sheet.write(row, 4, line.get('previous_stock', 0), normal_format)
            sheet.write(row, 5, line.get('stock_in', 0), normal_format)
            sheet.write(row, 6, line.get('sales_qty', 0), normal_format)
            sheet.write(row, 7, line.get('sales_refund_qty', 0), normal_format)
            sheet.write(row, 8, line.get('scrap_qty', 0), normal_format)
            sheet.write(row, 9, adjustment_qty, normal_format)
            sheet.write(row, 10, closing_stock, normal_format)
            sheet.write(row, 11, line.get('sales_amount', 0.0), normal_format)
            sheet.write(row, 12, line.get('discount_amount', 0.0), normal_format)
            sheet.write(row, 13, line.get('final_amount', 0.0), normal_format)
            row += 1

        row += 2

        workbook.close()
        output.seek(0)

        filename = f"Daily Product Sales and Inventory Report {self.shop_id.name}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
