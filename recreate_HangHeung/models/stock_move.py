from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_product_catalog_lines_data(self, parent_record=None, **kwargs):
        return {
            'quantity': sum(self.mapped('product_uom_qty')),
            'price': 0.0,
            'readOnly': parent_record._is_readonly() if parent_record else False,
        }
