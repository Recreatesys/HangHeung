from odoo import models, fields, api

class PaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    use_payment_terminal = fields.Selection(
        selection=lambda self: self._get_payment_terminal_selection(),
        string='Use a Payment Terminal',
        help='Record payments with a terminal on this journal.'
    )

    eft_user_confirm_key = fields.Char(string="Merchent Confirm Key")
    eft_secret_key = fields.Char(string="Merchent Secret Key")

    @api.model
    def _get_payment_terminal_selection(self):
        """Dynamically return available terminals based on config settings."""
        params = self.env['ir.config_parameter'].sudo()
        options = []

        if params.get_param('pos_eft.pos_alipay_enabled') == 'True':
            options.append(('alipay', 'Alipay'))
        if params.get_param('pos_eft.pos_wechat_enabled') == 'True':
            options.append(('wechat', 'WeChat Pay'))
        if params.get_param('pos_eft.pos_fps_enabled') == 'True':
            options.append(('fps', 'FPS'))
        if params.get_param('pos_eft.pos_payme_enabled') == 'True':
            options.append(('payme', 'PayMe'))
        if params.get_param('pos_eft.pos_unionpay_enabled') == 'True':
            options.append(('unionpay', 'UnionPay'))

        return options
