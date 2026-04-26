import logging
from collections import defaultdict

from odoo import _, fields, models
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


ACCOUNT_240001_CODE = '240001'
ACCOUNT_240002_CODE = '240002'
ACCOUNT_400001_CODE = '400001'
ACCOUNT_400010_CODE = '400010'

COUPON_PROGRAM_TYPES = ('coupons', 'gift_card', 'ewallet')
NON_COUPON_PROGRAM_TYPES = ('promotion', 'promo_code', 'buy_x_get_y', 'next_order_coupons', 'loyalty')


class PosSession(models.Model):
    _inherit = 'pos.session'

    coupon_adjustment_move_id = fields.Many2one(
        'account.move',
        string="Coupon Adjustment Move",
        readonly=True,
        copy=False,
    )

    def _create_account_move(self, *args, **kwargs):
        result = super()._create_account_move(*args, **kwargs)
        for session in self:
            try:
                session._create_coupon_adjustment_move()
            except Exception as e:
                _logger.exception(
                    "Coupon adjustment move creation failed for session %s: %s",
                    session.name, e,
                )
        return result

    def _create_coupon_adjustment_move(self):
        self.ensure_one()
        if self.coupon_adjustment_move_id:
            return

        accounts = self._get_coupon_accounts()
        if not accounts:
            return
        acc_240001, acc_240002, acc_400001, acc_400010 = accounts

        balances = defaultdict(float)
        for order in self._get_closed_orders():
            for line in order.lines:
                self._collect_coupon_adjustment_for_line(
                    line, balances, acc_240001, acc_240002, acc_400001, acc_400010,
                )

        if not balances or all(
            float_is_zero(v, precision_rounding=self.currency_id.rounding)
            for v in balances.values()
        ):
            return

        line_vals = []
        for account, signed in balances.items():
            if float_is_zero(signed, precision_rounding=self.currency_id.rounding):
                continue
            debit = signed if signed > 0 else 0.0
            credit = -signed if signed < 0 else 0.0
            line_vals.append((0, 0, {
                'account_id': account.id,
                'name': _('Coupon routing adjustment for session %s') % self.name,
                'debit': debit,
                'credit': credit,
            }))

        if not line_vals:
            return

        total_dr = sum(l[2]['debit'] for l in line_vals)
        total_cr = sum(l[2]['credit'] for l in line_vals)
        if not float_is_zero(total_dr - total_cr, precision_rounding=self.currency_id.rounding):
            _logger.warning(
                "Coupon adjustment for session %s does not balance: DR=%s CR=%s; "
                "adjustment move skipped to preserve accounting integrity.",
                self.name, total_dr, total_cr,
            )
            return

        journal = self.config_id.journal_id
        move = self.env['account.move'].sudo().create({
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': _('Coupon adjustment — session %s') % self.name,
            'company_id': self.company_id.id,
            'line_ids': line_vals,
        })
        move._post(soft=False)
        self.coupon_adjustment_move_id = move.id
        _logger.info(
            "Coupon adjustment move %s posted for session %s (%d lines, DR=%s CR=%s)",
            move.name, self.name, len(line_vals), total_dr, total_cr,
        )

    def _get_coupon_accounts(self):
        self.ensure_one()
        Account = self.env['account.account'].with_company(self.company_id)
        acc_240001 = Account.search([('code', '=', ACCOUNT_240001_CODE)], limit=1)
        acc_240002 = Account.search([('code', '=', ACCOUNT_240002_CODE)], limit=1)
        acc_400001 = Account.search([('code', '=', ACCOUNT_400001_CODE)], limit=1)
        acc_400010 = Account.search([('code', '=', ACCOUNT_400010_CODE)], limit=1)
        if not (acc_240001 and acc_240002 and acc_400001 and acc_400010):
            return None
        return acc_240001, acc_240002, acc_400001, acc_400010

    def _collect_coupon_adjustment_for_line(self, line, balances, acc_240001, acc_240002, acc_400001, acc_400010):
        product_tmpl = line.product_id.product_tmpl_id

        if line.is_reward_line and line.coupon_id:
            program = line.coupon_id.program_id
            if program.program_type in COUPON_PROGRAM_TYPES:
                face = abs(line.price_subtotal_incl)
                if face <= 0:
                    face = line.coupon_id.face_value or 0.0
                if face <= 0:
                    return
                sold_at = line.coupon_id.sold_at_amount or 0.0
                if 0 < sold_at < face:
                    disc_at_sale = face - sold_at
                else:
                    disc_at_sale = 0.0

                pos_discount_categ = self.env.ref(
                    'discount_coupans.product_category_pos_discount',
                    raise_if_not_found=False,
                )
                reward_in_pos_discount = bool(
                    pos_discount_categ
                    and product_tmpl.categ_id == pos_discount_categ
                )

                balances[acc_240001] += face
                balances[acc_240002] -= disc_at_sale
                if reward_in_pos_discount:
                    balances[acc_400010] -= (face - disc_at_sale)
                else:
                    balances[acc_400001] -= face
                    if disc_at_sale > 0:
                        balances[acc_400010] += disc_at_sale
                return

        if product_tmpl.is_coupon and line.qty > 0 and line.discount and line.discount > 0:
            discount_amount = line.qty * line.price_unit * (line.discount / 100.0)
            if discount_amount > 0:
                balances[acc_240002] += discount_amount
                balances[acc_240001] -= discount_amount
            return

        if (
            line.is_reward_line
            and not line.coupon_id
            and line.reward_id
            and line.reward_id.program_id.program_type in NON_COUPON_PROGRAM_TYPES
            and line.qty > 0
        ):
            negative_amount = abs(line.price_subtotal_incl)
            if negative_amount <= 0:
                return
            coupon_share = self._compute_coupon_share_in_order(line)
            if coupon_share > 0:
                D = negative_amount * coupon_share
                balances[acc_240002] += D
                balances[acc_400010] -= D
            return

    def _compute_coupon_share_in_order(self, reward_line):
        order = reward_line.order_id
        coupon_revenue = 0.0
        total_revenue = 0.0
        for ol in order.lines:
            if ol.is_reward_line:
                continue
            revenue = ol.price_subtotal_incl
            if revenue <= 0:
                continue
            total_revenue += revenue
            if ol.product_id.product_tmpl_id.is_coupon:
                coupon_revenue += revenue
        if total_revenue <= 0:
            return 0.0
        return coupon_revenue / total_revenue
