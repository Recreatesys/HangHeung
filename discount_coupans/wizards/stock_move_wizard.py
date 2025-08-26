from odoo import models, fields, api
from odoo.exceptions import ValidationError


class StockMoveAddWizard(models.TransientModel):
    _name = 'stock.move.add.wizard'
    _description = 'Add Stock Move Wizard'

    quantity = fields.Float(string="Quantity", default=1)
    product_id = fields.Many2one('product.product', string="Product", required=True, readonly=True)
    location_id = fields.Many2one('stock.location', string="Location", compute='_compute_location_id', store=False, readonly=True)
    picking_id = fields.Many2one('stock.picking', string="Picking", required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', store=True, readonly=False)
    lot_id_domain = fields.Char(string='Lot Domain', compute='_compute_lot_id_domain')

    @api.depends('product_id', 'picking_id')
    def _compute_location_id(self):
        for line in self:
            if line.picking_id and line.product_id:
                move = line.picking_id.move_ids.filtered(lambda m: m.product_id == line.product_id)[:1]
                line.location_id = move.location_id if move else False
            else:
                line.location_id = False

    @api.depends('product_id', 'location_id')
    def _compute_lot_id_domain(self):
        for line in self:
            if line.product_id and line.location_id:
                quant_lots = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', 'child_of', line.location_id.id),
                    ('quantity', '>', 0)
                ]).mapped('lot_id').ids
                line.lot_id_domain = str([('id', 'in', quant_lots)])
            elif line.product_id:
                lot_ids = self.env['stock.lot'].search([('product_id', '=', line.product_id.id)]).ids
                line.lot_id_domain = str([('id', 'in', lot_ids)])
            else:
                line.lot_id_domain = "[]"

    def action_confirm(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        demand_qty = sum(self.picking_id.move_ids.filtered(
            lambda m: m.product_id == self.product_id
        ).mapped(lambda m: m.product_uom_qty))

        if self.quantity > demand_qty:
            raise ValidationError(f"Quantity ({self.quantity}) cannot exceed remaining demand ({demand_qty}).")

        if not self.lot_id or not self.quantity or not self.location_id or not self.picking_id:
            return

        lots = self.env['stock.lot'].search([('product_id', '=', self.product_id.id),('id', '>=', self.lot_id.id)], order='name asc')

        selected_lots = lots[:int(self.quantity)]

        for lot in selected_lots:
            move_line_vals = {
                'picking_id': self.picking_id.id,
                'product_id': self.product_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.picking_id.location_dest_id.id,
                'lot_id': lot.id,
                'qty_done': 1,
            }
            self.env['stock.move.line'].create(move_line_vals)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
