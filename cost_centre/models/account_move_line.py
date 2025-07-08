from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    cost_center_id = fields.Many2one(
        'cost.centre',
        string='Cost Centre'
    )


