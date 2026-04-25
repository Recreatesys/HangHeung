from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    coupon_lot_range_display = fields.Char(
        compute='_compute_coupon_lot_range_display',
        string='Coupon Range',
    )

    @api.depends('move_line_ids.lot_id', 'product_id.is_coupon')
    def _compute_coupon_lot_range_display(self):
        for move in self:
            if not move.product_id.is_coupon:
                move.coupon_lot_range_display = False
                continue
            lot_names = sorted(
                {ml.lot_id.name for ml in move.move_line_ids if ml.lot_id and ml.lot_id.name}
            )
            if not lot_names:
                move.coupon_lot_range_display = False
            elif len(lot_names) == 1:
                move.coupon_lot_range_display = lot_names[0]
            else:
                move.coupon_lot_range_display = f"{lot_names[0]} - {lot_names[-1]}"

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
