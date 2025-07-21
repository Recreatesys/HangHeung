from odoo import models, fields, api, _
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
import re


class ResUsers(models.Model):
    _inherit = 'res.users'

    default_receipt_type = fields.Many2one(comodel_name="stock.picking.type", string="Default Receipt", store=True,  domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id), ('name', '=', 'Receipts')]")
    default_dest_address = fields.Many2one(comodel_name="res.partner", string="Default Address", store=True)
