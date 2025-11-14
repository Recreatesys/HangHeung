from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re

class LoyaltyAssignStoreWizard(models.TransientModel):
    _name = "loyalty.assign.store.wizard.range"
    _description = "Assign Store by Prefix and Range"

    line_ids = fields.One2many(
        'loyalty.assign.store.range.line',
        'wizard_id',
        string='Ranges to Assign',
        required=True
    )

    def action_assign_store(self):
        Card = self.env['loyalty.card']

        all_line_errors = []
        assign_candidates = []

        for idx, line in enumerate(self.line_ids, start=1):

            line_header = f"{line.prefix} {line.range_from}-{line.range_to}"
            line_issues = []

            if len(line.range_from) != len(line.range_to):
                line_issues.append(_("Range From and Range To should have same length (like 001 - 010)."))

            try:
                start = int(line.range_from)
                end = int(line.range_to)
            except (ValueError, TypeError):
                line_issues.append(_("Range From and Range To must be numeric strings (zero-padded)"))
                joined_issues = "\n ".join(line_issues)
                all_line_errors.append(f"{line_header}: {joined_issues}")
                continue

            if start >= end:
                line_issues.append(_(f'{line.prefix} Range From should be less than Range To.'))
                joined_issues = "\n ".join(line_issues)
                all_line_errors.append(f"{line_header}: {joined_issues}")
                continue

            cards = Card.search([('code', '=like', f"{line.prefix}%")])
            if not cards:
                line_issues.append(_("No coupons found with prefix %s.") % line.prefix)
                joined_issues = "\n ".join(line_issues)
                all_line_errors.append(f"{line_header}: {joined_issues}")
                continue

            filtered_cards = cards.filtered(lambda c: (
                c.code.startswith(line.prefix) and
                line.range_from <= c.code.replace(line.prefix, '') <= line.range_to
            ))

            length = len(line.range_from)
            expected_codes = [f"{line.prefix}{str(num).zfill(length)}" for num in range(start, end + 1)]
            existing_codes = set(filtered_cards.mapped('code'))
            missing_codes = sorted(set(expected_codes) - existing_codes)

            if missing_codes:
                show_missing = ", ".join(missing_codes[:10])
                if len(missing_codes) > 10:
                    show_missing += _(" ...(+%d more)") % (len(missing_codes) - 10)
                line_issues.append(_("Missing coupons: %s") % show_missing)

            already_assigned = filtered_cards.filtered(lambda c: c.allocated_store_id)
            if already_assigned:
                assigned_list = ", ".join(c.code for c in already_assigned[:10])
                if len(already_assigned) > 10:
                    assigned_list += _(" ...(+%d more)") % (len(already_assigned) - 10)
                line_issues.append(_("Already assigned: %s") % assigned_list)

            if line_issues:
                all_line_errors.append(f"{line_header}: {'; '.join(line_issues)}")
                continue

            for card in filtered_cards:
                assign_candidates.append((card, line.store_id.id))

        if all_line_errors:
            raise ValidationError("\n\n".join(all_line_errors))

        for card, store_id in assign_candidates:
            card.write({'allocated_store_id': store_id})

        return {'type': 'ir.actions.act_window_close'}



class LoyaltyAssignStoreRangeLine(models.TransientModel):
    _name = "loyalty.assign.store.range.line"
    _description = "Ranges for Store Assignment"

    wizard_id = fields.Many2one('loyalty.assign.store.wizard.range', ondelete='cascade')
    prefix = fields.Char("Prefix", required=True)
    range_from = fields.Char("Range From", required=True)
    range_to = fields.Char("Range To", required=True)
    store_id = fields.Many2one('pos.config', string="Store", required=True)
