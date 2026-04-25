from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    intercompany_source_po_name = fields.Char(
        string='PO No. from Hoymay',
        readonly=True,
        copy=False,
    )
