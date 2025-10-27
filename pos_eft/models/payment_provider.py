from odoo import models, fields

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    User_confirm_Key = fields.Char("User Confirm Key")
    Secret_code   = fields.Char("Secret Key")
  
