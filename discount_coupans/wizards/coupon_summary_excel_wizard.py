from odoo import models, fields, api, _
import base64
import io
import xlsxwriter
from odoo.exceptions import ValidationError

class CouponSummaryExcelWizard(models.TransientModel):
    _name = 'coupon.summary.excel.wizard'
    _description = 'Coupon Summary Excel Report Wizard'

    from_date = fields.Date('From Date', required=True)
    to_date = fields.Date('To Date', required=True)
    program_ids = fields.Many2many('loyalty.program', string="Coupon Programs", domain="[('program_type', '=', 'coupons')]",required=True)
    activated_shop_ids = fields.Many2many(
        'pos.config',
        'coupon_summary_activated_shop_rel',
        'wizard_id',
        'shop_id',
        string="Activated Shops",
    )

    sold_shop_ids = fields.Many2many(
        'pos.config',
        'coupon_summary_sold_shop_rel',
        'wizard_id',
        'shop_id',
        string="Sold To Shops"
    )
    file_data = fields.Binary('Excel File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)

    def action_generate_report_excel(self):
        domain = []
        if self.from_date:
            domain.append(('create_date', '>=', self.from_date))
        if self.to_date:
            domain.append(('create_date', '<=', self.to_date))
        if self.program_ids:
            domain.append(('program_id', 'in', self.program_ids.ids))
        if self.activated_shop_ids:
            domain.append(('allocated_store_id', 'in', self.activated_shop_ids.ids))
        if self.sold_shop_ids:
            domain.append(('redeem_shop_id', 'in', self.sold_shop_ids.ids))

        coupons = self.env['loyalty.card'].search(domain)
        if not coupons:
            raise ValidationError(_("No data found for the selected filters, Excel file will not be generated."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Coupon Summary')

        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#D9D9D9', 'align': 'center', 'valign': 'vcenter'
        })
        cell = workbook.add_format({'text_wrap': True, 'valign': 'top'})

        headers = [
            'Code', 'Prefix', 'Coupon Program', 'Activated Shop', 'Sold To Shop',
            'Status', 'Activation Date', 'Redeemed Date', 'Created Date'
        ]

        for col, title in enumerate(headers):
            sheet.write(0, col, title, header_format)

        row = 1
        for c in coupons:
            sheet.write(row, 0, c.code or '', cell)
            sheet.write(row, 1, c.prefix or '', cell)
            sheet.write(row, 2, c.program_id.name or '', cell)
            sheet.write(row, 3, c.allocated_store_id.display_name or '', cell)
            sheet.write(row, 4, c.redeem_shop_id.display_name or '', cell)
            sheet.write(row, 5, c.status.title() or '', cell)
            sheet.write(row, 6, str(c.date_activation or ''), cell)
            sheet.write(row, 7, str(c.date_sale or ''), cell)
            sheet.write(row, 8, str(c.create_date.date() if c.create_date else ''), cell)
            row += 1

        workbook.close()
        output.seek(0)

        self.write({
            'file_data': base64.b64encode(output.read()),
            'file_name': 'Coupon_consolidate_Report.xlsx'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model={self._name}&id={self.id}&field=file_data&filename_field=file_name&download=true",
            'target': 'self',
        }
