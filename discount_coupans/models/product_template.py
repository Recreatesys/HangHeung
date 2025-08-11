from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_coupon = fields.Boolean(string='Is Coupon', default=False, help="Check this box if this product is a coupon.")
    loyalty_program_id = fields.Many2one(
        "loyalty.program",
        string="Loyalty Program",
        required=True,
        store=True,
        help="Select the loyalty program associated with this coupon.",
        domain="[('program_type', '=', 'coupons')]"
    )
    store_id = fields.Many2one(
        'pos.config',
        string='Store',
        required=True,
        help="Select the store where this coupon can be redeemed."
    )