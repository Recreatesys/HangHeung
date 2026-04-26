import logging

from odoo import _, fields, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


ACCOUNT_240001_CODE = '240001'
ACCOUNT_240002_CODE = '240002'


class AccountMove(models.Model):
    _inherit = 'account.move'

    coupon_adjustment_move_id = fields.Many2one(
        'account.move',
        string="Coupon Adjustment Move",
        readonly=True,
        copy=False,
    )
    coupon_adjustment_source_move_id = fields.Many2one(
        'account.move',
        string="Source Invoice for Coupon Adjustment",
        readonly=True,
        copy=False,
    )

    def _post(self, soft=True):
        result = super()._post(soft=soft)
        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund') and m.state == 'posted'):
            cards_to_activate = self.env['loyalty.card']
            sold_at_per_card = {}
            for inv_line in move.invoice_line_ids:
                for so_line in inv_line.sale_line_ids:
                    cards = so_line.reserved_coupon_ids
                    if not cards:
                        continue
                    cards_to_activate |= cards
                    if inv_line.quantity:
                        per_unit = inv_line.price_subtotal / inv_line.quantity
                    else:
                        per_unit = 0.0
                    for card in cards:
                        sold_at_per_card[card.id] = per_unit
            if cards_to_activate:
                base_vals = {
                    'date_activation': fields.Datetime.now(),
                    'date_sale': fields.Datetime.now(),
                    'partner_id': move.partner_id.id or False,
                }
                for card in cards_to_activate:
                    vals = dict(base_vals)
                    if card.status != 'activated':
                        vals['status'] = 'activated'
                    if card.id in sold_at_per_card and not card.sold_at_amount:
                        vals['sold_at_amount'] = sold_at_per_card[card.id]
                    card.sudo().write(vals)

            try:
                move._create_coupon_invoice_adjustment_move()
            except Exception as e:
                _logger.exception(
                    "Coupon invoice adjustment failed for %s: %s",
                    move.name, e,
                )

        return result

    def _create_coupon_invoice_adjustment_move(self):
        self.ensure_one()
        if self.coupon_adjustment_move_id or self.coupon_adjustment_source_move_id:
            return

        company = self.company_id
        Account = self.env['account.account'].with_company(company)
        acc_240001 = Account.search([('code', '=', ACCOUNT_240001_CODE)], limit=1)
        acc_240002 = Account.search([('code', '=', ACCOUNT_240002_CODE)], limit=1)
        if not (acc_240001 and acc_240002):
            return

        total_discount = 0.0
        for line in self.invoice_line_ids:
            product_tmpl = line.product_id.product_tmpl_id
            if not product_tmpl.is_coupon:
                continue
            if not line.discount or line.discount <= 0:
                continue
            if line.quantity <= 0:
                continue
            gross = line.quantity * line.price_unit
            discount_amount = gross * (line.discount / 100.0)
            if discount_amount > 0:
                total_discount += discount_amount

        if float_is_zero(total_discount, precision_rounding=self.currency_id.rounding):
            return

        sign = -1 if self.move_type == 'out_refund' else 1
        adj_amount = total_discount * sign

        line_vals = [
            (0, 0, {
                'account_id': acc_240002.id,
                'name': _('Coupon sell-time discount carry — invoice %s') % self.name,
                'debit': adj_amount if adj_amount > 0 else 0.0,
                'credit': -adj_amount if adj_amount < 0 else 0.0,
            }),
            (0, 0, {
                'account_id': acc_240001.id,
                'name': _('Coupon sell-time discount carry — invoice %s') % self.name,
                'debit': -adj_amount if adj_amount < 0 else 0.0,
                'credit': adj_amount if adj_amount > 0 else 0.0,
            }),
        ]

        adj = self.env['account.move'].sudo().create({
            'journal_id': self.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': _('Coupon adjustment for %s') % self.name,
            'company_id': company.id,
            'line_ids': line_vals,
            'coupon_adjustment_source_move_id': self.id,
        })
        adj._post(soft=False)
        self.coupon_adjustment_move_id = adj.id
        _logger.info(
            "Coupon invoice adjustment %s posted for invoice %s (amount %s)",
            adj.name, self.name, total_discount,
        )
