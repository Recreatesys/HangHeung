from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        result = super()._post(soft=soft)
        for move in self.filtered(lambda m: m.move_type in ('out_invoice', 'out_refund') and m.state == 'posted'):
            cards_to_activate = self.env['loyalty.card']
            for inv_line in move.invoice_line_ids:
                for so_line in inv_line.sale_line_ids:
                    cards_to_activate |= so_line.reserved_coupon_ids
            cards_to_activate = cards_to_activate.filtered(
                lambda c: c.status != 'activated'
            )
            if cards_to_activate:
                cards_to_activate.sudo().write({
                    'status': 'activated',
                    'date_activation': fields.Datetime.now(),
                    'date_sale': fields.Datetime.now(),
                    'partner_id': move.partner_id.id or False,
                })
        return result
