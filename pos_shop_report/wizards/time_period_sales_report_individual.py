import io
import base64
import xlsxwriter
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class TimePeriodSalesReportIndividual(models.TransientModel):
    _name = 'time.period.sales.report.individual'
    _description = 'Time Period Sales Report (Individual Store)'

    shop_id = fields.Many2one('pos.config', string="Shop", required=True)
    date = fields.Date(string="Date", required=True)

    def action_generate_excel(self):
        company = self.env.company
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('時段銷售報告 / Time Period Sales Report')

        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({'bold': True, 'align': 'center'})
        money = workbook.add_format({'num_format': '#,##0.00'})

        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 18)
        sheet.set_column('C:C', 15)

        sheet.write(0, 0, company.name, bold)
        sheet.write(1, 0, "時段銷售報告")
        sheet.write(2, 0, "日期:")
        sheet.write(2, 1, str(self.date))
        sheet.write(3, 0, "分店:")
        sheet.write(3, 1, self.shop_id.name)

        headers = ["銷售時段", "銷售金額($)", "交易次數"]
        for col, h in enumerate(headers):
            sheet.write(5, col, h, header_format)

        row = 6

        slots = {
            "早(07:00 ~ 10:59)": range(7, 11),
            "午(11:00 ~ 17:59)": range(11, 18),
            "晚(18:00 ~ 23:59)": range(18, 24),
        }

        orders = self.env['pos.order'].search([
            ('state', 'in', ['paid', 'done', 'invoiced']),
            ('config_id', '=', self.shop_id.id),
            ('date_order', '>=', f"{self.date} 00:00:00"),
            ('date_order', '<=', f"{self.date} 23:59:59"),
            ('company_id', '=', company.id),
        ])

        if not orders:
            raise ValidationError(_('There are no orders for this date.'))

        grand_total = 0.0

        # Process each slot
        for slot_name, hours in slots.items():
            sheet.write(row, 0, slot_name, bold)
            row += 1

            slot_total = 0.0

            for hour in hours:
                slot_orders = orders.filtered(lambda o: fields.Datetime.context_timestamp(self.with_context(tz=self.env.user.tz), o.date_order).hour == hour)
                total_amount = sum(slot_orders.mapped('amount_total'))

                slot_total += total_amount

                sheet.write(row, 0, f"{hour:02d}:00 ~ {hour:02d}:59")
                sheet.write(row, 1, total_amount, money)
                sheet.write(row, 2, total_amount, money)
                row += 1

            # Subtotal for slot
            sheet.write(row, 0, f"{slot_name} 小計", bold)
            sheet.write(row, 1, slot_total, money)
            sheet.write(row, 2, slot_total, money)
            row += 2

            grand_total += slot_total

        # Grand total
        sheet.write(row, 0, "總數", bold)
        sheet.write(row, 1, grand_total, money)
        sheet.write(row, 2, grand_total, money)

        workbook.close()
        output.seek(0)

        filename = f"Time Period Sales Report {self.shop_id.name} {self.date}.xlsx"
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
