from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LoyaltyGenerateWizard(models.TransientModel):
    _inherit = 'loyalty.generate.wizard'

    prefix = fields.Char(string='Prefix', required=True)
    range_from = fields.Char(string='Range From', required=True)
    count = fields.Integer(string="Count", default=1)
    range_to = fields.Char(string='Range To', required=True, compute="_compute_range_to")
    active = fields.Boolean(string='Active', default=True)
    store_id = fields.Many2one('pos.config', string='Store')
    preactive_coupon = fields.Boolean(string="Pre-activate Coupon")

    @api.model
    def default_get(self, fields_list):
        res = super(LoyaltyGenerateWizard,self).default_get(fields_list)
        res['points_granted'] = 0
        return res

    @api.depends('range_from', 'count')
    def _compute_range_to(self):
        for record in self:
            if record.range_from and record.count:
                padding_len = len(record.range_from)
                start = int(record.range_from)
                end = start + record.count - 1
                record.range_to = str(end).zfill(padding_len)
            else:
                record.range_to = record.range_from

    def generate_coupons(self):
        self.ensure_one()
        if not self.program_id.product_id:
            raise ValidationError("Please assign a Product on the Loyalty Program before generating coupons.")
        created_cards = self.env['loyalty.card']
        if self.mode == 'selected' and self.customer_ids:
            for idx, customer in enumerate(self.customer_ids, start=1):
                card_vals = {
                    'prefix': self.prefix,
                    'range_from': str(idx),
                    'range_to': str(idx),
                    'expiration_date': self.valid_until,
                    'points': self.points_granted,
                    'store_id': self.store_id.id or '',
                    'partner_id': customer.id,
                }
                created_cards |= self.env['loyalty.card'].create(card_vals)
        else:
            card_vals = {
                'prefix': self.prefix,
                'range_from': self.range_from,
                'range_to': self.range_to,
                'expiration_date':self.valid_until,
                'points': self.points_granted,
                'store_id':self.store_id.id
            }
            created_cards |= self.env['loyalty.card'].create(card_vals)
        return {
            'res_model': 'loyalty.card',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_cards.ids)],
        }

    @api.onchange('mode')
    def _onchange_mode(self):
        for wizard in self:
            if wizard.mode == 'selected':
                wizard.range_from = '0'
                wizard.range_to= str(len(wizard._get_partners()))
            else:
                wizard.range_from = '0'
                wizard.range_to= '0'

    @api.onchange('customer_ids')
    def _onchange_customer(self):
        for wizard in self:
            if wizard.mode == 'selected':
                wizard.range_from = '1'
                wizard.range_to = str(len(self.customer_ids))
