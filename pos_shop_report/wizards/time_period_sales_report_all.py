from odoo import models, fields
import io
import base64
import xlsxwriter


class TimePeriodSalesReportAll(models.TransientModel):
    _name = 'time.period.sales.report.all'
    _description = 'Time Period Sales Wizard (All Stores)'

    date = fields.Date(string="Date", required=True)

    def action_generate_excel(self):
        company = self.env.company
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('時段銷售報告(全線) / Time Period Sales Report (All Stores)')

        bold = workbook.add_format({'bold': True})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        money = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})

        sheet.set_column(0, 0, 25)
        sheet.set_column('B:AA', 18)

        sheet.write(0, 0, company.name, bold)
        sheet.write(1, 0, "時段銷售報告(全線)")
        sheet.write(2, 0, "日期:")
        sheet.write(2, 1, str(self.date))

        stores = self.env['pos.config'].search([])
        slots = {
            "早(07:00 ~ 10:59)": range(7, 11),
            "午(11:00 ~ 17:59)": range(11, 18),
            "晚(18:00 ~ 23:59)": range(18, 24),
        }

        grand_totals = {store.id: {'amount': 0.0, 'count': 0} for store in stores}

        for store in stores:
            orders = self.env['pos.order'].search([
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('config_id', '=', store.id),
                ('date_order', '>=', f"{self.date} 00:00:00"),
                ('date_order', '<=', f"{self.date} 23:59:59"),
                ('company_id', '=', company.id),
            ])
            grand_totals[store.id]['amount'] = sum(orders.mapped('amount_total'))
            grand_totals[store.id]['count'] = len(orders)

        stores_with_data = [s for s in stores if grand_totals[s.id]['amount'] > 0]

        col = 1
        for store in stores_with_data:
            sheet.merge_range(4, col, 4, col + 1, store.name, header_format)
            sheet.write(5, col, "銷售金額($)", header_format)
            sheet.write(5, col + 1, "交易次數", header_format)
            col += 2

        sheet.merge_range(4, col, 4, col + 1, "Total", header_format)
        sheet.write(5, col, "總銷售金額($)", header_format)
        sheet.write(5, col + 1, "總交易次數", header_format)

        row = 6
        grand_total_amount = 0.0
        grand_total_count = 0

        for slot_name, hours in slots.items():
            sheet.write(row, 0, slot_name, bold)
            row += 1

            for hour in hours:
                sheet.write(row, 0, f"{hour:02d}:00 ~ {hour:02d}:59")
                col = 1
                total_amount_all = 0.0
                total_count_all = 0

                for store in stores_with_data:
                    orders = self.env['pos.order'].search([
                        ('state', 'in', ['paid', 'done', 'invoiced']),
                        ('config_id', '=', store.id),
                        ('date_order', '>=', f"{self.date} 00:00:00"),
                        ('date_order', '<=', f"{self.date} 23:59:59"),
                        ('company_id', '=', company.id),
                    ])

                    slot_orders = orders.filtered(
                        lambda o: fields.Datetime.context_timestamp(
                            self.with_context(tz=self.env.user.tz), o.date_order
                        ).hour == hour
                    )

                    total_amount = sum(slot_orders.mapped('amount_total'))
                    tx_count = len(slot_orders)

                    if total_amount:
                        sheet.write(row, col, total_amount, money)
                        sheet.write(row, col + 1, total_amount, money)
                    col += 2

                    total_amount_all += total_amount
                    total_count_all += tx_count

                # Totals
                sheet.write(row, col, total_amount_all if total_amount_all else "", money)
                sheet.write(row, col + 1, total_amount_all if total_amount_all else "", money)

                grand_total_amount += total_amount_all
                grand_total_count += total_count_all

                row += 1
            row += 1

        # Totals row
        sheet.write(row, 0, "總數", bold)
        col = 1
        for store in stores_with_data:
            sheet.write(row, col, grand_totals[store.id]['amount'], money)
            sheet.write(row, col + 1, grand_totals[store.id]['amount'], money)
            col += 2

        sheet.write(row, col, grand_total_amount, money)
        sheet.write(row, col + 1, grand_total_amount, money)

        workbook.close()
        output.seek(0)

        filename = f"Time Period Sales Report All Stores {self.date}.xlsx"
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
