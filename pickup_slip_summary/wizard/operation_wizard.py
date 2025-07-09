from odoo import models, fields
import io
import base64
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import UserError

class ReportInventoryWizard(models.TransientModel):
    _name = 'report.inventory.wizard'
    _description = 'Inventory Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True, default=fields.Date.context_today, readonly=True)

    def print_report(self):
        if self.start_date > self.end_date:
            raise UserError("Start Date cannot be after End Date.")

        picking_types = self.env['stock.picking.type'].search([])
        all_names = picking_types.mapped('warehouse_id.name')
        warehouse_codes = sorted(set(name.split('-')[0].strip() for name in all_names if name))

        pickings = self.env['stock.picking'].search([
            ('scheduled_date', '>=', self.start_date),
            ('scheduled_date', '<=', self.end_date),
            ('state', 'in', ['confirmed', 'assigned'])
        ])

        if not pickings:
            raise UserError("No records found in this date range.")

        product_set = set()
        report_data = {}
        product_uom_map = {}
        product_code_map = {}

        for picking in pickings:
            full_wh_name = picking.picking_type_id.warehouse_id.name or 'Unknown'
            warehouse_code = full_wh_name.split('-')[0].strip()

            if warehouse_code not in warehouse_codes:
                continue

            for move in picking.move_ids_without_package:
                product_name_full = move.product_id.display_name or 'Unknown'
                product_set.add(product_name_full)

                product_uom_map[product_name_full] = move.product_uom.name
                product_code_map[product_name_full] = move.product_id.default_code or ''

                report_data.setdefault(product_name_full, {}).setdefault(warehouse_code, 0)
                report_data[product_name_full][warehouse_code] += move.product_uom_qty

        sorted_products = sorted(product_set)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Inventory Report')

        sheet.set_column(0, 0, 20)
        sheet.set_column(1, 1, 40)
        sheet.set_column(2, 2, 10)
        for i in range(3, 3 + len(warehouse_codes)):
            sheet.set_column(i, i, 10)

        header_format = workbook.add_format({'bold': True, 'align': 'center'})

        sheet.write(0, 0, '')
        sheet.write(0, 1, '')
        sheet.write(0, 2, '', header_format)
        for col, wh in enumerate(warehouse_codes, start=3):
            sheet.write(0, col, wh, header_format)

        sheet.write(1, 0, 'Item Code', header_format)
        sheet.write(1, 1, 'Item Name', header_format)
        sheet.write(1, 2, 'UNIT', header_format)
        for col in range(3, 3 + len(warehouse_codes)):
            sheet.write(1, col, 'UNIT', header_format)

        total_by_wh = {wh: 0 for wh in warehouse_codes}
        row = 2

        for product_name in sorted_products:
            item_code = product_code_map.get(product_name, '')
            uom = product_uom_map.get(product_name, '')

            sheet.write(row, 0, item_code)
            sheet.write(row, 1, product_name)
            sheet.write(row, 2, uom)

            for col, wh in enumerate(warehouse_codes, start=3):
                qty = report_data.get(product_name, {}).get(wh, 0)
                sheet.write(row, col, qty)
                total_by_wh[wh] += qty

            row += 1

        sheet.write(row, 2, 'Total', header_format)
        for col, wh in enumerate(warehouse_codes, start=3):
            sheet.write(row, col, total_by_wh[wh], header_format)

        workbook.close()
        output.seek(0)
        xlsx_data = output.read()
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'Pickup Slip Summary.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'res_model': 'report.inventory.wizard',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        download_url = f'/web/content/{attachment.id}?download=true'
        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
