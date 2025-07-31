from odoo import models, fields, api
from lxml import etree
from odoo import http

from odoo.http import request
class PosRefundController(http.Controller):

    @http.route('/pos/get_payment_method_by_name', type='json', auth='user')
    def get_payment_method_by_name(self, name):
        order = request.env['pos.order'].sudo().search([('name', '=', name)], limit=1)
        if order and order.payment_ids:
            payment_method = order.payment_ids[0].payment_method_id
            return {
                'payment_method_id': payment_method.id,
                'refund_payment_method_id': payment_method.refund_payment_method.id if payment_method.refund_payment_method else False
            }
        return {'payment_method_id': False, 'refund_payment_method_id': False}


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
            if line.is_octopus and line.name:
                provider_name = line.name.lower()
                suffix = ''
                if 'octopus' in provider_name:
                    suffix_raw = provider_name.split('octopus')[-1]
                    suffix = suffix_raw.strip().lstrip('-').lstrip().upper()

                if suffix:
                    refund_name_variants = [
                        f"cash - {suffix}",
                        f"cash-{suffix}",
                        f"cash {suffix}",
                        f"cash{suffix}",
                    ]

                    refund_method = False
                    for name in refund_name_variants:
                        refund_method = self.env['pos.payment.method'].sudo().search([
                            ('name', 'ilike', name)
                        ], limit=1)
                        if refund_method:
                            break

                    line.refund_payment_method = refund_method.id if refund_method else False
                else:
                    refund_method_name = self.env['pos.payment.method'].sudo().search([
                            ('name', 'ilike', 'Cash')
                        ], limit=1)
                    line.refund_payment_method = refund_method_name
            else:
                line.refund_payment_method = False


class POSMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    payment_method_id = fields.Many2one(
        'pos.payment.method',
        string='Payment Method',
        help="Select the payment method for this transaction."
    )
    payment_method_id_domain = fields.Char(
        compute='_compute_payment_method_id_domain',
        help="Domain for the payment method selection."
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')

        if 'payment_method_id' in fields_list and active_id:
            refund_order = self.env['pos.order'].browse(active_id).exists()
            if refund_order and refund_order.name:
                original_order_name = refund_order.name.replace(' REFUND', '').strip()
                original_order = self.env['pos.order'].search([('name', '=', original_order_name)], limit=1)
                if original_order:
                    original_payment = self.env['pos.payment'].search([
                        ('pos_order_id', '=', original_order.id)
                    ], limit=1)
                    if original_payment and original_payment.payment_method_id.refund_payment_method:
                        # This is a refund — skip the default
                        defaults['payment_method_id'] = False

        return defaults

    @api.depends('payment_method_id')
    def _compute_payment_method_id_domain(self):
        for rec in self:
            domain = []
            active_id = self.env.context.get('active_id')

            if active_id:
                refund_order = self.env['pos.order'].browse(active_id).exists()
                if not refund_order or not refund_order.name:
                    return domain
                original_order_name = refund_order.name.replace(' REFUND', '').strip()
                original_order = self.env['pos.order'].search([('name', '=', original_order_name)], limit=1)
                if original_order:
                    original_payment = self.env['pos.payment'].search([('pos_order_id', '=', original_order.id)], limit=1)
                    if original_payment and original_payment.payment_method_id.refund_payment_method:
                        refund_method = original_payment.payment_method_id.refund_payment_method
                        domain = [('id', '=', refund_method.id)]
            rec.payment_method_id_domain = str(domain)