from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    show_all_product_stock = fields.Boolean(string='Show All products Stock')
    restrict_product = fields.Boolean(string='Restrict Product Out of Stock')
    stock_type = fields.Selection([('on_hand', 'Qty on Hand'),
                                   ('virtual', 'Virtual Qty'),
                                   ('both', 'Both')], string="Stock Type")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_all_product_stock = fields.Boolean(string='Show All products Stock',
                                            related="pos_config_id.show_all_product_stock",
                                            readonly=False)
    restrict_product = fields.Boolean(string='Restrict Product Out of Stock', related="pos_config_id.restrict_product",
                                      readonly=False)
    stock_type = fields.Selection([('on_hand', 'Qty on Hand'),
                                   ('virtual', 'Virtual Qty'),
                                   ('both', 'Both')], string="Stock Type", related="pos_config_id.stock_type",
                                  readonly=False)

    # @api.onchange('show_all_product_stock')
    # def _onchange_all_show_product(self):
    #     if self.show_all_product_stock:
    #         self.show_product_stock = False
    #
    # @api.onchange('show_product_stock')
    # def _onchange_show_product(self):
    #     if self.show_product_stock:
    #         self.show_all_product_stock = False
