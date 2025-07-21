from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockBackorderConfirmationCustom(models.TransientModel):
    _name = 'stock.backorder.confirmation.custom'
    _description = 'Custom Backorder Confirmation Wizard'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        help="The stock picking record that triggered this confirmation."
    )
    # Changed from Char to Many2one to link to the 'reason.code' model
    reason_code = fields.Many2one(
        'reason.code',
        string='Reason Code',
        required=True,
        help="Select a reason code for the partial delivery. This field is mandatory."
    )
    backorder_option = fields.Selection([
        ('create_backorder', 'Create Backorder'),
        ('no_backorder', 'No Backorder'),
    ],
        string='Backorder Option',
        default='create_backorder',
        required=True,
        help="Choose whether to create a backorder for the remaining quantity or not."
    )

    def _get_picking_to_validate(self):
        return self.picking_id

    def action_confirm(self):
        self.ensure_one()

        # The Many2one field 'reason_code' will be falsy if not selected
        if not self.reason_code:
            raise UserError(_("Reason Code is required. Please select a reason for the partial delivery."))

        picking = self._get_picking_to_validate()
        if not picking:
            raise UserError(_("No picking record found to validate. Please contact your administrator."))

        # Store the 'code' (Char) from the selected 'reason.code' record
        picking.custom_reason_code = self.reason_code.code

        context_for_action_done = {
            'do_not_create_backorder': (self.backorder_option == 'no_backorder'),
        }

        picking.with_context(**context_for_action_done)._action_done()

        return {'type': 'ir.actions.act_window_close'}

    def action_discard(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}