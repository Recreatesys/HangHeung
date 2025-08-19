from odoo import models, fields, _
from odoo.exceptions import ValidationError

class LoyaltyAssignStoreWizard(models.TransientModel):
    _name = "loyalty.assign.store.wizard"
    _description = "Loyalty Assign Store Wizard"

    store_id = fields.Many2one('pos.config', string='Store')

    def action_assign_store(self):
        Lot = self.env['stock.lot']
        selected_cards = self.env['loyalty.card'].browse(self._context.get('active_ids'))

        for card in selected_cards:
            if card.allocated_store_id:
                raise ValidationError(
                    _("The Loyalty Card '%s' is already assigned to store '%s'.") %
                    (card.code, card.allocated_store_id.display_name)
                )
            product = card.program_id.product_id
            code = card.code
            lot = Lot.search([('name', '=', code), ('product_id', '=', product.id)], limit=1)
            if not lot:
                lot = Lot.create({
                    'name': code,
                    'product_id': product.id,
                })
            warehouse = self.store_id.picking_type_id.warehouse_id
            location = warehouse.lot_stock_id or self.env.ref('stock.stock_location_stock')
            quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
                ('lot_id', '=', lot.id),
            ], limit=1)

            if not quant:
                self.env['stock.quant'].create({
                    'product_id': product.id,
                    'location_id': location.id,
                    'quantity': 1,
                    'lot_id': lot.id,
                })

            card.write({
                'allocated_store_id': self.store_id.id,
                'lot_id': lot.id
            })