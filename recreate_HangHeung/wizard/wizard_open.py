from odoo import models, fields,api

class WizardCode(models.TransientModel):
    _name = 'wizard.code'
    _description = 'Reason Code'

    reason_code_id = fields.Many2one(
        'reason.code',
        string='Reason Code',
        required=True,
    )

    def action_confirm_reason(self):
        """Apply reason_code_id to correct record based on its odoo_function value."""
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')

        if not active_id or not active_model:
            return {'type': 'ir.actions.act_window_close'}

        record = self.env[active_model].browse(active_id)
        if record and self.reason_code_id:
            record.reason_code = self.reason_code_id.id

        return {'type': 'ir.actions.act_window_close'}