from odoo import models, fields,api

class ReasonCode(models.Model):
    _name = 'reason.code'
    _description = 'Reason Code'
    _rec_name = 'code' 

    code = fields.Char(string='Reason Code', required=True)
    remark = fields.Char(string='Reason Remark',required=True)
    trx_type = fields.Selection([
        ('SAL', 'SAL'),
        ('ADJ', 'ADJ'),
        ('TRO', 'TRO'),
    ], string='Trx Type')
    priority = fields.Char(string='Priority')
    odoo_function_ids = fields.Many2many("stock.picking.type",string='Odoo Function')

    @api.depends('code', 'remark')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.remark}" if record.remark else record.code