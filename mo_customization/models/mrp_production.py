from odoo import models, api

class MrpProductionInherit(models.Model):
    _inherit = 'mrp.production'


    def action_confirm(self):
        res = super(MrpProductionInherit, self).action_confirm()
        for mo in self:
            bom = mo.bom_id
            if not bom:
                continue
            bom_qty_map = {line.product_id.id: line.product_qty for line in bom.bom_line_ids}
            
            for move in mo.move_raw_ids:
                product = move.product_id
                consumed_qty = move.product_uom_qty
                bom_qty = bom_qty_map.get(product.id, 0)
                
                if consumed_qty > bom_qty:
                    self.env['mrp.consumption.variance'].create({
                        'mo_id': mo.id,
                        'product_id': product.id,
                        'bom_qty': bom_qty,
                        'consumed_qty': consumed_qty,
                        'excess_qty': consumed_qty - bom_qty,
                    })
        return res
    