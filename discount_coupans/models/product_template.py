from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


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
        required=False,
        help="Select the store where this coupon can be redeemed."
    )

    @api.constrains('is_coupon', 'tracking')
    def _check_coupon_tracking_serial(self):
        for tmpl in self:
            if tmpl.is_coupon and tmpl.tracking != 'serial':
                raise ValidationError(_(
                    "Coupon product '%(name)s' must use Serial Number tracking (not '%(tracking)s'). "
                    "Each coupon code is a unique physical voucher and must be tracked one-to-one.",
                    name=tmpl.display_name, tracking=tmpl.tracking,
                ))