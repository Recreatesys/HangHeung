from odoo import models, fields, api


class ProductProduct(models.Model):
    _inherit = 'product.product'

    qty_available = fields.Float(string="Onhand Product Stock")
    virtual_available = fields.Float(string="Virtual Product Stock")

    # HH-CUSTOM: flag products whose stock is determined by something other
    # than their own qty_available -- POS combos (no own stock; choices
    # carry it) and phantom-BOM kits (own qty=0; component stock dictates).
    # Used by eg_pos_restrict_stock JS to skip the out-of-stock gate.
    pos_stock_skip_check = fields.Boolean(
        string="POS: skip stock check",
        compute='_compute_pos_stock_skip_check',
    )

    def _compute_pos_stock_skip_check(self):
        # product.template.type == 'combo'
        Bom = self.env['mrp.bom'] if 'mrp.bom' in self.env else None
        for p in self:
            if p.product_tmpl_id.type == 'combo':
                p.pos_stock_skip_check = True
                continue
            if Bom is not None:
                phantom = Bom.search([
                    '|',
                    ('product_id', '=', p.id),
                    '&', ('product_tmpl_id', '=', p.product_tmpl_id.id), ('product_id', '=', False),
                    ('type', '=', 'phantom'),
                ], limit=1)
                p.pos_stock_skip_check = bool(phantom)
            else:
                p.pos_stock_skip_check = False

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Returns the fields to be loaded for POS data."""
        result = super()._load_pos_data_fields(config_id)
        result.append('virtual_available')
        result.append('qty_available')
        result.append('pos_stock_skip_check')
        return result
