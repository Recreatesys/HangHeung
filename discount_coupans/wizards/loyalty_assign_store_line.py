from odoo import models, fields


class LoyaltyAssignStoreLine(models.TransientModel):
    _name = "loyalty.assign.store.line"
    _description = "Loyalty Assign Store Line"

    wizard_id = fields.Many2one('loyalty.assign.store.wizard', string='Wizard', required=True, ondelete='cascade')
    card_id = fields.Many2one('loyalty.card', string='Loyalty Card')
    store_id = fields.Many2one('pos.config', string='Store', ondelete='cascade',  required=False)
