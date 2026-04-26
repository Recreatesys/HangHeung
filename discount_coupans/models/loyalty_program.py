from odoo import models, fields, api, _

class LoyaltyProgramInherit(models.Model):
    _inherit = 'loyalty.program'

    product_id = fields.Many2one('product.product', string="Product", domain="[('is_coupon', '=', True),('is_storable', '=', True),('tracking', '=', 'serial')]")
