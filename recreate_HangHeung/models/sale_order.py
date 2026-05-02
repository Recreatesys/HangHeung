from odoo import models, fields, _, SUPERUSER_ID


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    intercompany_source_po_name = fields.Char(
        string='PO No. from Hoymay',
        readonly=True,
        copy=False,
    )

    remark = fields.Text(
        string='備註',
        copy=True,
        help=(
            "Free-text remark propagated through the intercompany chain: "
            "PO of Hoymay, SO/PO of That's, SO of HangHeung. Carried by every "
            "downstream record automatically."
        ),
    )

    is_wedding_order = fields.Boolean(
        string='嫁囍單',
        default=False,
        copy=False,
        help=(
            "When ticked, on confirmation this SO and its entire intercompany "
            "chain are isolated -- never merged with other orders. One dedicated "
            "PO/SO per flagged record at every chain step."
        ),
    )

    is_b2b_order = fields.Boolean(
        string='B2B單',
        default=False,
        copy=False,
        help=(
            "When ticked, on confirmation this SO and its entire intercompany "
            "chain are isolated -- never merged with other orders. One dedicated "
            "PO/SO per flagged record at every chain step."
        ),
    )

    def _prepare_purchase_order_data(self, *args, **kwargs):
        """Intercompany SO -> PO: carry remark + isolation flags onto the PO."""
        result = super()._prepare_purchase_order_data(*args, **kwargs)
        if isinstance(result, dict):
            result['remark'] = self.remark or False
            result['is_wedding_order'] = self.is_wedding_order
            result['is_b2b_order'] = self.is_b2b_order
        return result

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
