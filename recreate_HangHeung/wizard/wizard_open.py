from odoo import models, fields,api

class WizardCode(models.TransientModel):
    _name = 'wizard.code'
    _description = 'Reason Code'

    reason_code_id = fields.Many2one(
        'reason.code',
        string='Reason Code',
        required=True,
    )