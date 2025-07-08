from odoo import models, fields

class CostCentre(models.Model):
    _name = 'cost.centre'
    _description = 'Cost Centre'

    name = fields.Char(string='Name', required=True)