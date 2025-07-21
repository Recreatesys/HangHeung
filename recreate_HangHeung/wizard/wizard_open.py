from odoo import models, fields,api

class WizardCode(models.TransientModel):
    _name = 'wizard.code'
    _description = 'Reason Code'


    reason_code_id = fields.Many2one(
        'reason.code',
        string='Reason Code',
        required=True,
    )
    operations = fields.Char(
        string='Operations',
        readonly=True,
        compute='_compute_operations',
    )

    @api.depends('reason_code_id')
    def _compute_operations(self):
        for wizard in self:
            if wizard.reason_code_id:
                wizard.operations = wizard.reason_code_id.odoo_function or 'N/A'
            else:
                wizard.operations = ''

    def action_confirm_reason(self):
        """Apply reason_code_id to correct record based on its odoo_function value."""
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')

        if not active_id or not active_model:
            return
        import pdb; pdb.set_trace();

        record = self.env[active_model].browse(active_id)
        # import pdb; pdb.set_trace();

        if self.reason_code_id.odoo_function == 'Receipt':
            if record._name == 'account.move' and record.move_type == 'out_refund':
                record.reason_code_id = self.reason_code_id.id
            

        elif self.reason_code_id.odoo_function == 'delivery':
            if record._name == 'account.move' and record.move_type in ('in_invoice', 'in_refund'):
                record.reason_code_id = self.reason_code_id.id

        # Optional: handle other odoo_function values here

        return {'type': 'ir.actions.act_window_close'}
