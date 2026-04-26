from odoo import _, api, models
from odoo.exceptions import ValidationError


class DiscountConfig(models.Model):
    _inherit = 'discount.config'

    @api.constrains('discount_product')
    def _check_discount_product_pos_discount_category(self):
        pos_discount_categ = self.env.ref(
            'discount_coupans.product_category_pos_discount',
            raise_if_not_found=False,
        )
        if not pos_discount_categ:
            return
        for record in self:
            product = record.discount_product
            if product and product.categ_id != pos_discount_categ:
                raise ValidationError(_(
                    "The Discount Product %(product)s must belong to the "
                    "'POS Discount' product category so the journal entry "
                    "routes to account 400010 POS Discount.",
                    product=product.display_name,
                ))
