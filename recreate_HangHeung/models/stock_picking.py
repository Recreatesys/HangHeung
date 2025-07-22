from odoo import models, fields, api, _
import logging
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError
from odoo.tools import format_list


_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    has_dropship_origin = fields.Boolean(string='Has Dropship', default=False, compute="_compute_has_dropship")
    dropship_validated = fields.Boolean(string='Dropship Validated', default=False)
    reason_code = fields.Many2one('reason.code',string='Reason Code')


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
        for picking in self:
            for move in picking.move_ids:
                if move.scrapped:
                    continue
                if move.product_uom_qty > move.quantity:
                    move.picked = True
                    view =  self.env.ref('recreate_HangHeung.view_reason_wizard_form1')
                    return {
                        'name': 'Provide Reason Code',
                        'type': 'ir.actions.act_window',
                        'res_model': 'wizard.code',
                        'view_mode': 'form',
                        'view_id': self.env.ref('recreate_HangHeung.view_reason_wizard_form1').id,
                        'target': 'new',
                        'context': {
                            'default_reason_code_id': False,
                            'active_id': picking.id,
                            'active_model': 'stock.picking',
                        }
                    }

        # Normal flow if no condition met
        if not self.env.context.get('skip_backorder'):
            pickings_to_backorder = self._check_backorder()
            if pickings_to_backorder:
                return pickings_to_backorder._action_generate_backorder_wizard(
                    show_transfers=self._should_show_transfers()
                )
        return True