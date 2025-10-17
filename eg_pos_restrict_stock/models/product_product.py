from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_available = fields.Float(string="Onhand Product Stock")
    virtual_available = fields.Float(string="Virtual Product Stock")

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Returns the fields to be loaded for POS data."""
        result = super()._load_pos_data_fields(config_id)
        result.append('virtual_available')
        result.append('qty_available')
        return result
