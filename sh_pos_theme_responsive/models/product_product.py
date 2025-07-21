from odoo import models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_product_info_pos(self, price, quantity, pos_config_id):
        res = super().get_product_info_pos(price, quantity, pos_config_id)

        config = self.env['pos.config'].browse(pos_config_id)
        warehouse_list = [
            {
                'id': w.id,
                'name': w.name,
                'available_quantity': self.with_context({'warehouse_id': w.id}).qty_available,
                'forecasted_quantity': self.with_context({'warehouse_id': w.id}).virtual_available,
                'uom': self.uom_name
            }
            for w in self.env['pos.config'].search([('id', '=', config.id),('company_id', '=', config.company_id.id)]).warehouse_id
        ]

        res['warehouses'] = warehouse_list
        return res
