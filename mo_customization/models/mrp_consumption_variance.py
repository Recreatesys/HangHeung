from odoo import models, fields

class MrpConsumptionVariance(models.Model):
    _name = 'mrp.consumption.variance'
    _description = "Mrp Consumption Variance"
    _order = 'id desc'
    
    mo_id = fields.Many2one('mrp.production', string="Manufacturing Order", required=True, readonly=True)
    product_id = fields.Many2one('product.product', string="Componenet", requried=True, readonly=True)
    bom_qty = fields.Float(string="BOM Quantity", required=True, readonly=True)
    consumed_qty = fields.Float(string="Consumed Quantity", required=True, readonly=True)
    excess_qty = fields.Float(string="Excess Quantity", required=True, readonly=True)