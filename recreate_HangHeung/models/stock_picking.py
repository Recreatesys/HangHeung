from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_dropship_origin = fields.Boolean(string='Has Dropship', default=False, compute="_compute_has_dropship")
    dropship_validated = fields.Boolean(string='Dropship Validated', default=False)

    reason_code = fields.Many2one(
        'reason.code',
        string='Reason Code',
        domain="[('odoo_function_ids', 'in', picking_type_id)]",
        store=True
    )

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        for record in self:
            record.reason_code = False

    def _compute_has_dropship(self):
        for record in self:
            if record.origin:
                origin_po = record.origin.split('-')[-1].strip()

                dropship = self.env['stock.picking'].with_company(2).search([
                    ('origin', '=', origin_po),
                    ('picking_type_id.code', '=', 'dropship')
                ], limit=1)

                record.has_dropship_origin = bool(dropship)
            else:
                record.has_dropship_origin = False

    def button_dropship_validate(self):
        if self.origin:
            origin_po = self.origin.split('-')[-1].strip()

            dropship = self.env['stock.picking'].with_company(2).search([
                ('origin', '=', origin_po),
                ('picking_type_id.code', '=', 'dropship')
            ], limit=1)

            if dropship:
                dropship.button_validate()
                dropship.message_post(
                    body=_("The dropship order %s has been successfully validated by %s.") % (dropship.name, self.company_id.name)
                )
                self.message_post(body=_("Dropship order %s has been successfully validated") % (dropship.name))
                self.dropship_validated = True
                dropship.dropship_validated = True

    def _pre_action_done_hook(self):
        res = super(StockPicking, self)._pre_action_done_hook()
        for picking in self:
            for move in picking.move_ids:
                if move.scrapped:
                    continue
                if move.product_uom_qty > move.quantity:
                    move.picked = True
                    return {
                        'name': 'Provide Reason Code',
                        'type': 'ir.actions.act_window',
                        'res_model': 'wizard.code',
                        'view_mode': 'form',
                        'view_id': self.env.ref('recreate_HangHeung.view_reason_wizard_form1').id,
                        'target': 'new',
                        'context': {
                            'picking_type_id': picking.picking_type_id.id,
                            'active_id': picking.id,
                            'active_model': 'stock.picking',
                        }
                    }
        return res