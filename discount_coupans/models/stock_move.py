from odoo import models, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)

        for move in moves:
            if not move.picking_id or not move.picking_id.origin:
                continue

            sale_order = self.env['sale.order'].search([('name', '=', move.picking_id.origin)], limit=1)
            if not sale_order:
                continue

            for line in sale_order.order_line:
                if line.product_id == move.product_id and line.product_id.is_coupon:

                    loyalty_cards = self.env['loyalty.card'].search([
                        ('program_id', '=', line.product_id.loyalty_program_id.id),
                        ('store_id', '=', line.product_id.store_id.id),
                        ('status', '=', 'not_activated'),
                        ('lot_id', '!=', False),
                    ], limit=int(line.product_uom_qty))

                   
                    lot_ids = loyalty_cards.mapped('lot_id').ids
                    if lot_ids:
                        move.lot_ids = [(6, 0, lot_ids)]

        return moves
