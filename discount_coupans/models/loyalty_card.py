from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class LoyaltyCard(models.Model):
    _inherit = 'loyalty.card'

    prefix = fields.Char(string='Prefix', required=True, store=True)
    range_from = fields.Char(string='Range From', required=True, store=True)
    range_to = fields.Char(string='Range To', required=True, store=True)
    lot_id = fields.Many2one('stock.lot', string="Linked Lot")

    store_id = fields.Many2one('pos.config', string='Store')
    allocated_store_id = fields.Many2one('pos.config', string="Allocated Store", readonly=True)
    code = fields.Char(string='Code', readonly=True, required=False, copy=False,default=False)
    
    status = fields.Selection([
        ('not_activated', 'Not Activated'),
        ('activated', 'Activated'),
        ('invalid', 'Invalid'),
        ('redeemed', 'Redeemed'),
    ], string="Coupon Status", tracking=True, default='not_activated')

    date_activation = fields.Datetime(string="Activation Date", readonly=True)
    date_sale = fields.Datetime(string="Sale Date", readonly=True)
    redeem_shop_id = fields.Many2one('pos.config', string="Redeemed At", readonly=True)
    redeemed_datetime = fields.Datetime(string="Redeemed Date", readonly=True)

    remark = fields.Text(string='Internal Remark', help="Used for internal notes or memos. Not visible on printed coupon.")

    expiration_type = fields.Selection([
        ('fixed', 'Fixed Expiration Date'),
        ('post_activation', 'Valid after Activation'),
    ], string="Expiration Type", default='post_activation', required=True)

    validity_days = fields.Integer(string="Validity Duration (Days)", default=1825)

    effective_expiration = fields.Date(string="Effective Expiration", compute="_compute_dynamic_expiration_date", store=False)

    allocated_date = fields.Date(string='Allocated Date', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('allocated_store_id') and not vals.get('allocated_date'):
            vals['allocated_date'] = fields.Date.today()
        return super().create(vals)

    def write(self, vals):
        if 'allocated_store_id' in vals and not vals.get('allocated_date'):
            vals['allocated_date'] = fields.Date.today()
        return super().write(vals)

    @api.depends('date_activation', 'validity_days', 'expiration_type')
    def _compute_dynamic_expiration_date(self):
        for record in self:
            if record.expiration_type == 'post_activation' and record.date_activation:
                record.effective_expiration = record.date_activation.date() + timedelta(days=record.validity_days)
            elif record.expiration_type == 'fixed':
                record.effective_expiration = record.expiration_date
            else:
                record.effective_expiration = False

    @api.model
    def create(self, vals):
        if vals.get('range_from') and vals.get('range_to') and vals.get('prefix'):
            try:
                range_from = int(vals['range_from'])
                range_to = int(vals['range_to'])
            except ValueError:
                raise ValidationError("Range From and Range To must be numeric.")

            if range_from > range_to:
                raise ValidationError("Range From cannot be greater than Range To.")

            number_length = max(len(vals['range_from']), len(vals['range_to']))
            created_cards = []

            for number in range(range_from, range_to + 1):
                code = f"{vals['prefix']}{str(number).zfill(number_length)}"
                card_vals = vals.copy()
                card_vals['code'] = code
                card_vals['range_from'] = str(number).zfill(number_length)
                card_vals['range_to'] = str(number).zfill(number_length)
                card = super(LoyaltyCard, self).create(card_vals)
                created_cards.append(card)

            return created_cards[0]
        else:
            return super(LoyaltyCard, self).create(vals)

    @api.model
    def update_loyalty_from_pos(self, product_data):
        for item in product_data:
            partner_id = item.get('customer_id')
            for lot_no in item.get('lots', []):
                card = self.search([('code', '=', lot_no)], limit=1)
                if card:
                    wizard = self.env['loyalty.card.update.balance'].create({
                        'card_id': card.id,
                        'old_balance': card.points_display,
                        'new_balance': 1,
                        'description': 'Updated from POS sale',
                    })
                    wizard.action_update_card_point()
                    card.write({
                        'status': 'activated',
                        'partner_id': partner_id or False,
                        'date_activation': fields.datetime.now(),
                    })
        return True

    @api.model
    def update_coupon_redeem_from_pos(self, vals):
        coupon_code = vals.get("coupon_code")
        store_id = vals.get("store_id")

        if coupon_code:
            card = self.search([('code', '=', coupon_code)])
            if card:
                card.write({
                    'redeem_shop_id': store_id,
                })
        return True

class LoyaltyHistory(models.Model):
    _inherit = 'loyalty.history'

    salesperson_id = fields.Many2one('res.users', string="Salesperson", readonly=True)
