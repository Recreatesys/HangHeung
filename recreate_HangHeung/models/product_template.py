from odoo import models, fields, api, _
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    old_item_number = fields.Char(string='Old Item Number', stored=True)
    alternate_item_name = fields.Char(string='Alternate Name', stored=True)
    alternate_unit_of_measure = fields.Many2one(
        'uom.uom', 
        string='Alternate Unit of Measure', 
        stored=True
    )
    conversion_rate = fields.Integer(string='Conversion Rate', stored=True)
    remarks = fields.Char(string='Remarks', stored=True)
    brand = fields.Char(string='Brand', stored=True)
    net_weight = fields.Char(string='Net Weight', stored=True)