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
