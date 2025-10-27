from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_alipay_enabled = fields.Boolean("Alipay", config_parameter='pos_eft.pos_alipay_enabled')
    pos_wechat_enabled = fields.Boolean("WeChat Pay", config_parameter='pos_eft.pos_wechat_enabled')
    pos_fps_enabled = fields.Boolean("FPS", config_parameter='pos_eft.pos_fps_enabled')
    pos_payme_enabled = fields.Boolean("PayMe", config_parameter='pos_eft.pos_payme_enabled')
    pos_unionpay_enabled = fields.Boolean("UnionPay", config_parameter='pos_eft.pos_unionpay_enabled')
