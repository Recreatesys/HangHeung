from odoo import models, fields, _, api
from odoo.exceptions import ValidationError

class LoyaltyAssignStoreWizard(models.TransientModel):
    _name = "loyalty.assign.store.wizard"
    _description = "Loyalty Assign Store Wizard"

    line_ids = fields.One2many('loyalty.assign.store.line', 'wizard_id', string='Cards to Assign')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        lines = [(0, 0, {'card_id': card.id}) for card in self.env['loyalty.card'].browse(active_ids)]
        res['line_ids'] = lines
        return res

    def action_assign_store(self):
        if not self.line_ids:
            raise ValidationError(_("No cards found in the wizard. Please reopen and try again."))

        Lot = self.env['stock.lot']
        Quant = self.env['stock.quant']

        for line in self.line_ids:
            card = line.card_id

            if card.status not in ['not_activated']:
                raise ValidationError(_(
                    "The Loyalty Card '%s' cannot be assigned because its status is '%s'."
                ) % (card.code, card.status))

            product = card.program_id.product_id
            if not product:
                raise ValidationError(_("No product found for program '%s' linked to card '%s'.") %
                    (card.program_id.display_name, card.code))

            lot = Lot.search([('name', '=', card.code), ('product_id', '=', product.id)], limit=1)
            if not lot:
                lot = Lot.create({'name': card.code, 'product_id': product.id})

            warehouse = line.store_id.picking_type_id.warehouse_id
            location = warehouse.lot_stock_id or self.env.ref('stock.stock_location_stock')

            quant = Quant.search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
                ('lot_id', '=', lot.id),
            ], limit=1)
            if not quant:
                Quant.create({
                    'product_id': product.id,
                    'location_id': location.id,
                    'quantity': 1,
                    'lot_id': lot.id,
                })

            card.write({'allocated_store_id': line.store_id.id, 'lot_id': lot.id})
