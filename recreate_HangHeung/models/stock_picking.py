from odoo import models, fields, api, _
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        if self.company_id.id == 3 and self.picking_type_id.id == 221:
            if self.origin:
                origin_po = self.origin.split('-')[-1].strip()

                dropship = self.env['stock.picking'].with_company(2).search([
                    ('origin', '=', origin_po),
                    ('picking_type_id.code', '=', 'dropship')
                ], limit=1)

                _logger.info(f'Dropship order found: {dropship}')

                if dropship:
                    # Avoid Recursion
                    self.validate_dropship_order(dropship)

        return res

    def validate_dropship_order(self, dropship):
        if dropship:
            if dropship.state not in ['done', 'cancel']:
                _logger.info(f'Dropship order state before validation: {dropship.state}')
                dropship.button_validate()
