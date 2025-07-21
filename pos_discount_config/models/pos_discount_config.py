from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DiscountConfig(models.Model):
    _name = 'discount.config'
    _description = 'POS Discount Configuration'
    _rec_name = 'display_name'

    discount_apply_on = fields.Selection([
        ('product', 'Product'),
        ('category', 'Category')
    ], string="Apply Discount On", required=True, default='product')

    product_id = fields.Many2one('product.product', string="Product", domain="[('available_in_pos', '=', True)]")
    categ_ids = fields.Many2many('pos.category', string='Product Category',
                                 help="Category used in the Point of Sale.")
    discount_product = fields.Many2one('product.product', string="Discount Product",
                                       required=True, domain="[('available_in_pos', '=', True)]")
    discount_line_ids = fields.One2many('discount.config.line', 'config_id', string="Discount Lines")

    start_date = fields.Datetime(string="Start Date", required=True)
    end_date = fields.Datetime(string="End Date", required=True)

    company_id = fields.Many2one('res.company', string="Company",
                                 required=True, default=lambda self: self.env.user.company_id)
    pos_config_ids = fields.Many2many('pos.config', string='Point of Sale')

    display_name = fields.Char(string="Name", compute="_compute_display_name", store=True)

    @api.depends('discount_apply_on', 'product_id', 'categ_ids')
    def _compute_display_name(self):
        for record in self:
            if record.discount_apply_on == 'product':
                record.display_name = record.product_id.display_name or "Product Discount"
            else:
                categories = ', '.join(record.categ_ids.mapped('name'))
                record.display_name = f"Category: {categories}" if categories else "Category Discount"

    @api.constrains('start_date', 'end_date')
    def _check_date_range(self):
        for record in self:
            if record.start_date and record.end_date and record.end_date < record.start_date:
                raise ValidationError("End Date cannot be earlier than Start Date.")

    @api.constrains('discount_apply_on', 'product_id', 'categ_ids')
    def _check_discount_target(self):
        for rec in self:
            if rec.discount_apply_on == 'product' and not rec.product_id:
                raise ValidationError("Please select a product for discount.")
            if rec.discount_apply_on == 'category' and not rec.categ_ids:
                raise ValidationError("Please select at least one category for discount.")

    _sql_constraints = [
        ('product_unique', 'unique(product_id)', 'Configuration already exists for this product.')
    ]


class DiscountConfigLine(models.Model):
    _name = 'discount.config.line'
    _description = 'POS Discount Line'

    config_id = fields.Many2one('discount.config', string="Discount Config", required=True, ondelete='cascade')
    from_quantity = fields.Integer(string="From Quantity", required=True)
    to_quantity = fields.Integer(string="To Quantity")
    discount_amount = fields.Float(string="Discount Amount", required=True)

    _sql_constraints = [
        ('quantity_range_unique', 'unique(config_id, from_quantity, to_quantity)',
         'Exact same quantity range already exists for this product.')
    ]

    @api.constrains('from_quantity', 'to_quantity', 'discount_amount', 'config_id')
    def _check_validations(self):
        for rec in self:
            if rec.from_quantity <= 0:
                raise ValidationError("From Quantity should be greater than 0.")

            if rec.to_quantity < 0:
                raise ValidationError("To Quantity must be positive.")

            if rec.discount_amount < 0:
                raise ValidationError("Discount Amount cannot be negative.")

            if rec.to_quantity != 0 and rec.from_quantity > rec.to_quantity:
                raise ValidationError("From Quantity cannot be greater than To Quantity.")

            rec_from = rec.from_quantity
            rec_to = rec.to_quantity if rec.to_quantity > 0 else rec.from_quantity

            overlapping_lines = self.search([
                ('config_id', '=', rec.config_id.id),
                ('id', '!=', rec.id),
            ])

            for line in overlapping_lines:
                line_from = line.from_quantity
                line_to = line.to_quantity if line.to_quantity > 0 else line.from_quantity

                if rec_from <= line_to and rec_to >= line_from:
                    raise ValidationError(
                        f"Quantity range {rec_from} → {rec_to} "
                        f"overlaps with existing range {line_from} → {line_to}."
                    )

            product = rec.config_id.product_id
            if product:
                unit_price = product.lst_price or 0
                total_price = unit_price * rec.from_quantity
                if rec.discount_amount > total_price:
                    raise ValidationError(
                        f"Discount amount ({rec.discount_amount}) cannot be greater than total price "
                        f"({unit_price} × {rec.from_quantity} = {total_price})."
                    )
