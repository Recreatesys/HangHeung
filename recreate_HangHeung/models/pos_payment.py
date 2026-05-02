"""POS payment hook: when a payment is recorded against a POS order that is
settling a sale.order, confirm the deferred Hoymay PO that the SO created on
its initial confirm. The PO confirmation triggers the standard intercompany
SO/PO cascade (That's, HangHeung) downstream.
"""
import logging

from odoo import models, api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = 'pos.payment'

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        # Trigger PO confirm at the first partial payment per the user spec.
        try:
            payments._maybe_confirm_linked_pos(reason="POS payment recorded")
        except Exception as e:
            _logger.exception(
                "Failed to confirm deferred POs from POS payment(s) %s: %s",
                payments.ids, e,
            )
        return payments

    def _maybe_confirm_linked_pos(self, reason=""):
        """Find sale.orders linked to this payment's POS order through line
        sale_order_origin_id, then look for any draft Hoymay POs whose origin
        contains those SO names. Confirm them once."""
        Purchase = self.env['purchase.order'].sudo()
        for payment in self:
            order = payment.pos_order_id
            if not order:
                continue
            sale_orders = order.lines.mapped('sale_order_origin_id')
            if not sale_orders:
                continue
            for so in sale_orders:
                # Find draft, Hoymay (company 1) POs whose origin includes
                # this SO's name. Confirm each once.
                pos = Purchase.search([
                    ('company_id', '=', 1),
                    ('state', '=', 'draft'),
                    ('origin', 'like', so.name),
                ])
                pos = pos.filtered(
                    lambda p: any(
                        so.name == part.split('-')[-1].strip()
                        for part in (p.origin or '').split(', ')
                    )
                )
                if not pos:
                    continue
                pos.with_user(SUPERUSER_ID).button_confirm()
                for po in pos:
                    po.message_post(body=(
                        "Confirmed via POS settlement of %(so)s (%(reason)s)."
                        % {'so': so.name, 'reason': reason or 'POS payment'}
                    ))
                    _logger.info(
                        "Confirmed deferred PO %s on POS payment of SO %s",
                        po.name, so.name,
                    )
