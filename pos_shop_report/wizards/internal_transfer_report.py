from odoo import models, fields,api
import xlsxwriter
import base64
from io import BytesIO
from datetime import datetime
import pytz


class InternalTransferReportWizard(models.TransientModel):
    _name = 'internal.transfer.report.wizard'
    _description = 'Internal Transfer Report Wizard'

    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)    

    def action_export_xlsx(self):
        self.ensure_one()
        transfers = self.env['stock.picking'].search([
            ('picking_type_code', '=', 'internal'),
            ('scheduled_date', '>=', self.date_from),
            ('scheduled_date', '<=', self.date_to)
        ])

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Internal Transfer Report')

        bold = workbook.add_format({'bold': True, 'border': 1})
        normal = workbook.add_format({'border': 1})

        headers = [
            ' V Stock Transfer Trx No', 'V Stock Transfer Trx Date', 'V Stock Transfer Sh Code', 'V Stock Transfer Item Code', 'V Stock Transfer Item Name',
            'V Stock Transfer Item Unit', 'V Stock Transfer Qty', 'Reason Code', 'V Stock Transfer Location'
        ]

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(0, col, header, bold)

        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 25)
        sheet.set_column(3, 3, 15)
        sheet.set_column(4, 4, 30)
        sheet.set_column(5, 5, 10)
        sheet.set_column(6, 6, 12)
        sheet.set_column(7, 7, 15)
        sheet.set_column(8, 8, 25)

        row = 1
        for transfer in transfers:
            for move in transfer.move_ids:
                sheet.write(row, 0, transfer.name or '', normal)
                sheet.write(row, 1, str(transfer.scheduled_date or ''), normal)
                sheet.write(row, 2, transfer.location_id.display_name or '', normal)
                sheet.write(row, 3, move.product_id.default_code or '', normal)
                sheet.write(row, 4, move.product_id.name or '', normal)
                sheet.write(row, 5, move.product_uom.name or '', normal)
                sheet.write(row, 6, move.quantity or 0, normal)
                sheet.write(row, 7, getattr(transfer, 'reason_code', False) and transfer.reason_code.code or '', normal)
                sheet.write(row, 8, transfer.location_dest_id.display_name or '', normal)
                row += 1

        workbook.close()
        output.seek(0)

        file_data = base64.b64encode(output.read())
        output.close()

        formatted_date = datetime.now().strftime('%d-%m-%Y')
        attachment = self.env['ir.attachment'].create({
            'name': f"Internal Transfer Report {formatted_date}.xlsx",
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


