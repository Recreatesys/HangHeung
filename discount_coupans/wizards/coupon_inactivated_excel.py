from odoo import models, fields
import base64
import io
import xlsxwriter


class CouponInactivatedExcelWizard(models.TransientModel):
    _name = 'coupon.inactivated.excel.wizard'
    _description = 'Inactivated Coupon Excel Wizard'

    file_data = fields.Binary('Excel File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)

    def action_generate_excel(self):
        coupons = self.env['loyalty.card'].search([
            ('status', '=', 'not_activated'),
            ('program_id.program_type', '=', 'coupons')
        ])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Inactivated Coupons')

        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F4CCCC',
            'align': 'center',
            'valign': 'vcenter'
        })
        cell_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})

        headers = ['Code', 'Prefix', 'Store', 'Status', 'Activation Date']

        sheet.set_column(0, 0, 20, cell_format)  
        sheet.set_column(1, 1, 15, cell_format)  
        sheet.set_column(2, 2, 30, cell_format)  
        sheet.set_column(3, 3, 20, cell_format) 
        sheet.set_column(4, 4, 25, cell_format)  

        
        for col, head in enumerate(headers):
            sheet.write(0, col, head, header_format)

        row = 1
        for coupon in coupons:
            sheet.write(row, 0, coupon.code or '', cell_format)
            sheet.write(row, 1, coupon.prefix or '', cell_format)
            sheet.write(row, 2, coupon.store_id.display_name or '', cell_format)
            sheet.write(row, 3, 'Not Activated' or '', cell_format)
            sheet.write(row, 4, str(coupon.date_activation or ''), cell_format)
            row += 1

        workbook.close()
        output.seek(0)
        excel_data = output.read()

        self.write({
            'file_data': base64.b64encode(excel_data),
            'file_name': 'Inactivated_Coupons.xlsx',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }
