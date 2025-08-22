from odoo import models, fields, api

class LoyaltyGenerateWizard(models.TransientModel):
    _inherit = "loyalty.generate.wizard"

    preactive_coupon = fields.Boolean(string="Pre-activate Coupon",)

    def generate_coupons(self):
        old_coupons = self.env['loyalty.card'].search([
            ('program_id', '=', self.program_id.id)
        ])
        res = super().generate_coupons()

        if self.preactive_coupon:
            new_coupons = self.env['loyalty.card'].search([
                ('program_id', '=', self.program_id.id),
                ('id', 'not in', old_coupons.ids)
            ])
            new_coupons.write({
                'status': 'activated',
                'date_activation': fields.Datetime.now()})

        return res

