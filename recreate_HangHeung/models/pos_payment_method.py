from odoo import models, fields, api


class POSPPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_octopus = fields.Boolean(string='Is Octopus Payment Method', default=False)
    refund_payment_method = fields.Many2one(
        'pos.payment.method',
        string='Refund Payment Method',
        help="Select the payment method to use for refunds."
    )

    @api.onchange('is_octopus')
    def onchange_is_octopus(self):
        for line in self:
            if line.is_octopus:
                payment_method = self.env['pos.payment.method'].sudo().search([('name', 'ilike', 'cash')], limit=1)
                line.refund_payment_method = payment_method.id

class POSMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')

        if active_id:
            refund_order = self.env['pos.order'].browse(active_id).exists()
            if not refund_order or not refund_order.name:
                return defaults
            original_order_name = refund_order.name.replace(' REFUND', '').strip()
            original_order = self.env['pos.order'].search([('name', '=', original_order_name)], limit=1)
            if original_order:
                original_payment = self.env['pos.payment'].search([('pos_order_id', '=', original_order.id)], limit=1)
                if original_payment and original_payment.payment_method_id.refund_payment_method:
                    defaults['payment_method_id'] = original_payment.payment_method_id.refund_payment_method.id

        return defaults
