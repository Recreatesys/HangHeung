from odoo import _, api, models
from odoo.exceptions import ValidationError


NON_COUPON_PROGRAM_TYPES = ('promotion', 'promo_code', 'buy_x_get_y', 'next_order_coupons')


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    def _get_discount_product_values(self):
        """Auto-assign the 'POS Discount' product category when core creates
        the per-reward discount line product, so the downstream
        _check_discount_line_product_pos_discount_category constraint is
        satisfied without manual intervention. Only applies when the
        program is a non-coupon promotion-style program."""
        values = super()._get_discount_product_values()
        pos_discount_categ = self.env.ref(
            'discount_coupans.product_category_pos_discount',
            raise_if_not_found=False,
        )
        if not pos_discount_categ:
            return values
        for reward, vals in zip(self, values):
            if reward.program_id.program_type in NON_COUPON_PROGRAM_TYPES:
                vals['categ_id'] = pos_discount_categ.id
        return values

    @api.constrains('discount_line_product_id', 'program_id')
    def _check_discount_line_product_pos_discount_category(self):
        pos_discount_categ = self.env.ref(
            'discount_coupans.product_category_pos_discount',
            raise_if_not_found=False,
        )
        if not pos_discount_categ:
            return
        for reward in self:
            program = reward.program_id
            product = reward.discount_line_product_id
            if not product or not program:
                continue
            if program.program_type not in NON_COUPON_PROGRAM_TYPES:
                continue
            if product.categ_id != pos_discount_categ:
                raise ValidationError(_(
                    "The discount line product %(product)s on program %(program)s "
                    "must belong to the 'POS Discount' product category so the journal "
                    "entry routes to account 400010 POS Discount.",
                    product=product.display_name, program=program.display_name,
                ))
