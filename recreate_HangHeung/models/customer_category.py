from odoo import models, fields

class CustomerCategory(models.Model):
    _name = 'customer.category'
    _description = 'Customer Category'

    name = fields.Char(string='Category Name', required=True)