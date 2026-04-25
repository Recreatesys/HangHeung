from odoo import models, fields, _, SUPERUSER_ID


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    intercompany_source_po_name = fields.Char(
        string='PO No. from Hoymay',
        readonly=True,
        copy=False,
    )

    def _action_cancel(self):
        result = super()._action_cancel()
        Purchase = self.env['purchase.order']
        for so in self:
            ic_pos = Purchase.sudo().search([
                ('auto_sale_order_id', '=', so.id),
                ('state', 'not in', ('cancel', 'draft')),
            ])
            proc_candidates = Purchase.sudo().search([
                ('company_id', '=', so.company_id.id),
                ('auto_generated', '=', False),
                ('origin', 'like', so.name),
                ('state', 'not in', ('cancel', 'draft')),
            ])
            proc_pos = proc_candidates.filtered(
                lambda p: any(
                    so.name in part.split('-')
                    for part in (p.origin or '').split(', ')
                )
            )
            downstream_pos = ic_pos | proc_pos
            if downstream_pos:
                downstream_pos.with_user(SUPERUSER_ID).button_cancel()
                for po in downstream_pos:
                    po.message_post(body=_(
                        "Cancelled via chain cascade from %(so_name)s (company %(company)s).",
                        so_name=so.name, company=so.company_id.name,
                    ))
        return result
