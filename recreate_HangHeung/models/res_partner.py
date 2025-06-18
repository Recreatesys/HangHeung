from odoo import models, fields, api, _
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer = fields.Boolean(string='Customer', default=False, stored=True)
    vendor = fields.Boolean(string='Vendor', default=False, stored=True)
    contact_number = fields.Char(string='Contact No.', stored=True)
    alternative_contact_name = fields.Char(string='Alternative Name', stored=True)
    fax_number = fields.Char(string='Fax No.', stored=True)
    customer_credit_limit = fields.Integer(string='Credit Limit', default=0, stored=True)
    crdr_due_days = fields.Integer(string='CRDR Due Days', default=0, stored=True)
    customer_category_id = fields.Many2one(
        'customer.category', 
        string='Customer Category'
    )
    terms = fields.Char(string='Terms', stored=True)
    purchase_auto_confirm = fields.Boolean(string="Purchase Auto Confirm")
    has_moves = fields.Boolean(string="Has Moves")

   