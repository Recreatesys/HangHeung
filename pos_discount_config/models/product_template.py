from odoo import models, fields,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_discount = fields.Boolean(string="Exclude from Discount")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['is_discount']

    @api.constrains('is_discount')
    def find_is_discount(self):
        for template in self:
            if template.is_discount:
                products = self.env['product.product'].search([('product_tmpl_id', '=', template.id)])
                products.write({'is_discount': True})
            else:
                products = self.env['product.product'].search([('product_tmpl_id', '=', template.id)])
                products.write({'is_discount': False})

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_discount = fields.Boolean(string="Exclude from Discount")

    @api.model
    def _load_pos_data_fields(self, config_id):
        base_fields = super()._load_pos_data_fields(config_id)
        custom_fields = [
            'is_discount',
            'combo_ids',
            'product_tmpl_id',
            'image_128',
            'product_template_variant_value_ids',
        ]
        return list(set(base_fields + custom_fields))
