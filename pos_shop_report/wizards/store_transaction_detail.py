from odoo import models, fields, _
import io
import xlsxwriter
import base64
from odoo.exceptions import ValidationError


class POSShopStoreTransactionWizard(models.TransientModel):
    _name = 'pos.shop.store.transaction.report.wizard'
    _description = 'POS Shop Store Transaction Report Wizard'

    shop_id = fields.Many2one('pos.config', string='Shop', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)

    def generate_report(self):
        company = self.env.company
        orders = self.env['pos.order'].search([
            ('config_id', '=', self.shop_id.id),
            ('date_order', '>=', self.date_start),
            ('date_order', '<=', self.date_end),
            ('company_id', '=', company.id),
        ])

        if not orders:
            raise ValidationError(_('There are no orders for this date.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("分店交易明細")

        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'border': 1})
        wrap_format = workbook.add_format({'text_wrap': True})

        row = 0
        worksheet.write(row, 0, company.name, title_format)
        row += 1

        worksheet.write(row, 0, "分店交易明細", title_format)
        row += 2

        headers = [
            "日期", "交易時間", "分店", "訂單編號",
            "訂單內容", "數量", "交易金額",
            "付款方式", "電子支付參考編號", "備註"
        ]
        col_widths = [len(h) for h in headers]

        for col, h in enumerate(headers):
            worksheet.write(row, col, h, header_format)
        row += 1

        for order in orders:
            payment = order.payment_ids[:1] and order.payment_ids[0] or None
            first_line = True

            for line in order.lines:
                if first_line:
                    values = [
                        order.date_order.date().strftime("%d/%m/%Y"),
                        order.date_order.strftime("%H:%M:%S"),
                        order.config_id.name,
                        order.pos_reference or order.name,
                        line.product_id.display_name,
                        str(int(line.qty)),
                        f"{order.amount_total:.2f}",
                        payment.payment_method_id.name if payment else '',
                        payment.transaction_id if payment and payment.transaction_id else '',
                        order.general_note or ''
                    ]
                    first_line = False
                else:
                    values = [
                        "", "", "", "",
                        line.product_id.display_name,
                        str(int(line.qty)),
                        "", "", "", ""
                    ]

                for col, val in enumerate(values):
                    worksheet.write(row, col, val, wrap_format if col == 4 else None)
                    col_widths[col] = max(col_widths[col], len(str(val)))
                row += 1

        for i, width in enumerate(col_widths):
            worksheet.set_column(i, i, width + 2)

        workbook.close()
        output.seek(0)

        filename = f"Store Transactions {self.shop_id.name}.xlsx"
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

