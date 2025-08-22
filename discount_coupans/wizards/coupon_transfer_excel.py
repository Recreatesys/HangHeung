from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter

class CouponTransferExcelWizard(models.TransientModel):
    _name = 'coupon.transfer.excel.wizard'
    _description = 'Transfer Coupon Excel Wizard'

    shop_id = fields.Many2one('pos.config', string='Shop', required=True)
    date = fields.Date('Date', required=True)
    file = fields.Binary('Excel File')
    filename = fields.Char('File Name')

    def action_generate_transfer_excel(self):
        cards = self.env['loyalty.card'].search([
            ('allocated_store_id', '=', self.shop_id.id),
            ('allocated_date', '=', self.date)
        ])
        if not cards:
            raise UserError(_('No coupons found for the selected store on this date.'))

        coupon_ranges = {}
        for card in cards:
            program = card.program_id
            if program not in coupon_ranges:
                coupon_ranges[program] = {'min': card.code, 'max': card.code}
            else:
                if card.code < coupon_ranges[program]['min']:
                    coupon_ranges[program]['min'] = card.code
                if card.code > coupon_ranges[program]['max']:
                    coupon_ranges[program]['max'] = card.code

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Coupon Transfer')

        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 25)

        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True})

        worksheet.write('A1', '禮券到舖表', title_format)
        worksheet.write('A2', '產生 日期：')
        worksheet.write('B2', self.date.strftime("%d/%m/%Y"))
        worksheet.write('A3', '店舖')
        worksheet.write('B3',  self.shop_id.name)

        worksheet.write('A5', 'Coupon Name', header_format)
        worksheet.write('B5', 'Coupon Code Range', header_format)

        row = 5
        for program, codes in coupon_ranges.items():
            worksheet.write(row, 0, program.name)
            worksheet.write(row, 1, f"{codes['min']} - {codes['max']}")
            row += 1

        workbook.close()
        output.seek(0)
        data = output.read()

        self.file = base64.b64encode(data)
        self.filename = f'Coupon Transfer {self.shop_id.name} {self.date}.xlsx'

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/file/{self.filename}?download=true',
            'target': 'self',
        }
