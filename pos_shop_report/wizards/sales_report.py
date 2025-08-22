from odoo import models, fields
import base64
import io
import xlsxwriter
from datetime import datetime,date
from collections import defaultdict
from odoo.exceptions import ValidationError

class SalesReportExcelWizard(models.TransientModel):
    _name = 'sales.report.excel.wizard'
    _description = 'Sales Report Excel Wizard'

    def default_start_date(self):
        today = date.today()
        return today.replace(day=1)

    file_data = fields.Binary('Excel File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)
    start_date = fields.Date('Start Date',default=default_start_date)
    end_date = fields.Date('End Date',default=fields.Date.context_today)
    pos = fields.Many2one('pos.config')

    def action_generate_excel(self):
        """Generate POS Sales Excel and attach"""
        # Fetch POS Orders
        domain = [('state', 'in', ['paid', 'done', 'invoiced'])]
        cancel_domain = [('state', 'in', ['cancel'])]
        if self.start_date:
            domain.append(('date_order', '>=', self.start_date))
            cancel_domain.append(('date_order', '>=', self.start_date))
        if self.end_date:
            domain.append(('date_order', '<=', self.end_date))
            cancel_domain.append(('date_order', '<=', self.end_date))
        if self.pos:
            domain.append(('config_id', '=', self.pos.id))
            cancel_domain.append(('config_id', '=', self.pos.id))

        orders = self.env['pos.order'].search(domain)
        cancel_orders = self.env['pos.order'].search(cancel_domain)
        if not orders and not cancel_orders:
            raise ValidationError("No POS orders found for the selected date range and POS.")

        # Generate Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Sales Report")

        # Styles
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align':'left'})
        # text_format = workbook.add_format({'border': 1})
        cell_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'align':'left'})
        cell_value_format = workbook.add_format({'text_wrap': True, 'valign': 'top','border': 1, 'align':'left'})
        cell_value_format_bold = workbook.add_format({'bold': True,'text_wrap': True, 'valign': 'top','border': 1, 'align':'left'})

        sheet.set_column(0, 0, 20, cell_format)
        sheet.set_column(1, 1, 20, cell_format)
        sheet.set_column(2, 2, 30, cell_format)
        sheet.set_column(3, 3, 30, cell_format)
        sheet.set_column(4, 4, 30, cell_format)

        order_total = 0
        for order in orders:
            order_total += order.amount_total

        cancel_order_total = 0
        cancel_qty = 0
        for order in cancel_orders:
            cancel_order_total += order.amount_total
            for line in orders.mapped("lines"):
                cancel_qty += line.qty


        discount_products = self.env['discount.config'].search([]).mapped('product_id')
        loyal_reward_products = self.env['loyalty.reward'].search([]).mapped('discount_line_product_id')
        discount_ids = discount_products.ids + loyal_reward_products.ids

        summary = defaultdict(lambda: {"total_discount": 0.0, "count": 0})

        for line in orders.mapped("lines"):
            if line.product_id.id in discount_ids:
                pname = line.product_id.display_name
                summary[pname]["total_discount"] += line.price_subtotal_incl
                summary[pname]["count"] += 1



        total_amount = 0
        total_transcation = 0
        payment_summary = defaultdict(lambda: {"total_amount": 0.0, "transactions": 0})

        for payment in orders.mapped("payment_ids"):
            method = payment.payment_method_id.name or "Unknown"
            payment_summary[method]["total_amount"] += payment.amount
            payment_summary[method]["transactions"] += 1
            total_amount += payment.amount
            total_transcation += 1

        row = 1
        sheet.write(row,0,"日期:",header_format)
        sheet.write(row,1,self.start_date.strftime('%Y-%m-%d'),cell_value_format)
        row += 1
        sheet.write(row, 0, "(日結)時間:",header_format)
        sheet.write(row, 1, self.end_date.strftime('%Y-%m-%d'),cell_value_format)

        row += 1
        sheet.write(row, 0, "分店:",header_format)
        if self.pos:
            sheet.write(row, 1, self.pos.name,cell_value_format)
        else:
            sheet.write(row, 1, '', cell_value_format)


        row += 1
        sheet.write(row, 0, "總計($) :",header_format)
        sheet.write(row, 1, order_total, cell_value_format)

        row += 1
        sheet.write(row, 0, "交易數量 :",header_format)
        sheet.write(row, 1, total_transcation, cell_value_format)

        row += 2
        sheet.write(row, 0, "支付方式(小標題)",header_format)
        sheet.write(row, 1, "Amount",header_format)
        sheet.write(row, 2, "Transactions",header_format)

        row += 1

        for method, vals in payment_summary.items():
            sheet.write(row, 0, method, cell_value_format)
            sheet.write_number(row, 1, vals["total_amount"], cell_value_format)
            sheet.write_number(row, 2, vals["transactions"], cell_value_format)
            row += 1


        sheet.write(row, 0, "淨收入:", cell_value_format_bold)
        sheet.write(row, 1, total_amount, cell_value_format)
        sheet.write(row, 2, total_transcation, cell_value_format)

        row += 2

        sheet.write(row, 0, "折扣及優惠劵(小標題)", header_format)
        sheet.write(row, 1, "Amount discount", header_format)
        sheet.write(row, 2, "Discount used", header_format)

        row += 1

        for discount, vals in summary.items():
            sheet.write(row, 0, discount, cell_value_format)
            sheet.write_number(row, 1, vals["total_discount"], cell_value_format)
            sheet.write_number(row, 2, vals["count"], cell_value_format)
            row += 1

        row += 1

        sheet.write(row, 0, "Void單(小標題)", header_format)
        sheet.write(row, 1, '', cell_value_format)
        row += 1
        sheet.write(row, 0, "Void單數量:", header_format)
        sheet.write(row, 1, cancel_qty, cell_value_format)
        row += 1
        sheet.write(row, 0, "總金額:", header_format)
        sheet.write(row, 1, cancel_order_total, cell_value_format)
        row += 1

        workbook.close()
        output.seek(0)
        excel_data = output.read()

        # Save to wizard fields
        filename = f"Sales Report {datetime.today().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': filename,
        })

        self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(excel_data),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }
