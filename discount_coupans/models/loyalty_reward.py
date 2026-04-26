from odoo import _, api, models
from odoo.exceptions import ValidationError


NON_COUPON_PROGRAM_TYPES = ('promotion', 'promo_code', 'buy_x_get_y', 'next_order_coupons')


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

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
