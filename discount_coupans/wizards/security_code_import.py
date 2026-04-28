import base64
import io
import logging
import re

from odoo import models, fields, _, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ALLOWED_PREFIXES = ('HHC', 'BWC', 'CWC', 'EWC', 'DPC')
TRAILING_DIGITS = 2


class SecurityCodeImportWizard(models.TransientModel):
    _name = 'loyalty.security.code.import.wizard'
    _description = 'Import Coupon Security Codes from Excel'

    file_data = fields.Binary(string='Excel File', required=True)
    file_name = fields.Char(string='File Name')
    result_summary = fields.Text(string='Import Result', readonly=True)

    def action_import(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Please upload an Excel file first."))

        try:
            from openpyxl import load_workbook
        except ImportError:
            raise UserError(_("openpyxl is required to import Excel files."))

        try:
            wb = load_workbook(
                io.BytesIO(base64.b64decode(self.file_data)),
                read_only=True,
                data_only=True,
            )
        except Exception as e:
            raise UserError(_("Failed to open Excel file: %s") % e)

        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        wb.close()

        if not rows:
            raise UserError(_("Excel file is empty."))

        header_skipped = False
        if rows and rows[0]:
            first = str(rows[0][0]).strip() if rows[0][0] is not None else ''
            if first and not re.fullmatch(r'[A-Z]{3}\d+', first):
                rows = rows[1:]
                header_skipped = True

        Card = self.env['loyalty.card']
        updated = 0
        no_change = 0
        skipped = 0
        errors = []

        start_row_no = 2 if header_skipped else 1
        for offset, row in enumerate(rows):
            row_no = start_row_no + offset
            if not row or all(c is None or c == '' for c in row[:2]):
                continue

            code_val = str(row[0]).strip() if row[0] is not None else ''
            sec_val = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ''

            if not code_val:
                skipped += 1
                errors.append(_("Row %s: empty coupon code") % row_no)
                continue
            if not sec_val:
                skipped += 1
                errors.append(_("Row %s (%s): empty security code") % (row_no, code_val))
                continue

            prefix = code_val[:3].upper()
            if prefix not in ALLOWED_PREFIXES:
                skipped += 1
                errors.append(_(
                    "Row %s (%s): prefix '%s' not in allowed set %s"
                ) % (row_no, code_val, prefix, ', '.join(ALLOWED_PREFIXES)))
                continue

            expected_pattern = re.escape(code_val) + r'\d{%d}' % TRAILING_DIGITS
            if not re.fullmatch(expected_pattern, sec_val):
                skipped += 1
                errors.append(_(
                    "Row %s (%s): security code '%s' must be coupon code + %s digits"
                ) % (row_no, code_val, sec_val, TRAILING_DIGITS))
                continue

            card = Card.search([('code', '=', code_val)], limit=1)
            if not card:
                skipped += 1
                errors.append(_("Row %s (%s): coupon not found in DB") % (row_no, code_val))
                continue

            if card.security_code == sec_val:
                no_change += 1
                continue

            try:
                card.write({'security_code': sec_val})
                updated += 1
            except Exception as e:
                skipped += 1
                errors.append(_("Row %s (%s): %s") % (row_no, code_val, str(e)))

        if len(errors) > 50:
            errors = errors[:50] + [_("... %s more errors omitted") % (len(errors) - 50)]

        summary_lines = [
            _("Updated: %s") % updated,
            _("Already up-to-date: %s") % no_change,
            _("Skipped: %s") % skipped,
        ]
        if errors:
            summary_lines.append('')
            summary_lines.append(_("Errors:"))
            summary_lines.extend(errors)

        self.result_summary = '\n'.join(summary_lines)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
