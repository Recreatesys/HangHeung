from datetime import timedelta

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError


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

    @api.constrains('partner_shipping_id', 'commitment_date', 'order_line', 'state')
    def _check_pre_order_required_fields(self):
        """Once an SO leaves draft, delivery address, delivery date, and at
        least one line are mandatory."""
        for order in self:
            if order.state not in ('sale', 'done', 'sent'):
                continue
            if not order.partner_shipping_id:
                raise ValidationError(_("送貨地址 (Delivery Address) 必須填寫，不能留空。"))
            if not order.commitment_date:
                raise ValidationError(_("送貨日期 (Delivery Date) 必須填寫，不能留空。"))
            if not order.order_line:
                raise ValidationError(_("訂單必須最少包含一個產品 (Order line cannot be empty)."))

    @api.constrains('date_order', 'commitment_date')
    def _check_commitment_date_min_lead(self):
        """Delivery Date must be at least 1 day (24 hours) beyond the Order Date."""
        for order in self:
            if not order.commitment_date or not order.date_order:
                continue
            min_date = order.date_order + timedelta(days=1)
            if order.commitment_date < min_date:
                raise ValidationError(_(
                    "送貨日期必須在訂單日期之後最少 1 天 (24 小時)。\n"
                    "訂單日期:%(o)s\n"
                    "最早可選送貨日期:%(m)s",
                    o=fields.Datetime.to_string(order.date_order),
                    m=fields.Datetime.to_string(min_date),
                ))

    pickup_date_display = fields.Char(
        string='取貨日期 (display)',
        compute='_compute_pickup_display',
        store=False,
        help="Server-rendered commitment_date string for the POS receipt.",
    )
    pickup_address_display = fields.Char(
        string='取貨地點 (display)',
        compute='_compute_pickup_display',
        store=False,
        help=(
            "Server-rendered partner_shipping_id summary (name + address) "
            "for the POS receipt -- avoids relying on the partner record "
            "being in POS state, which it may not be for internal shop "
            "partners filtered out by the POS group rules."
        ),
    )

    @api.depends('commitment_date', 'partner_shipping_id', 'partner_shipping_id.name', 'partner_shipping_id.street', 'partner_shipping_id.street2', 'partner_shipping_id.city')
    def _compute_pickup_display(self):
        for order in self:
            if order.commitment_date:
                order.pickup_date_display = fields.Datetime.to_string(order.commitment_date)[:16]
            else:
                order.pickup_date_display = False
            ship = order.partner_shipping_id
            if ship:
                parts = [ship.name or '', ship.street or '', ship.street2 or '', ship.city or '']
                cleaned = [p.strip() for p in parts if p and p.strip()]
                order.pickup_address_display = ' — '.join(cleaned) if cleaned else False
            else:
                order.pickup_address_display = False

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Add commitment_date + pre-rendered display strings so the POS
        receipt can show 取貨日期 / 取貨地點 without depending on
        partner_shipping_id being in POS state (it may be filtered out by
        the POS group rule for internal shop partners)."""
        fields_list = super()._load_pos_data_fields(config_id)
        for f in ('commitment_date', 'pickup_date_display', 'pickup_address_display'):
            if f not in fields_list:
                fields_list = list(fields_list) + [f]
        return fields_list

    def _prepare_purchase_order_data(self, *args, **kwargs):
        """Intercompany SO -> PO: carry remark + isolation flags + dest_address."""
        result = super()._prepare_purchase_order_data(*args, **kwargs)
        if isinstance(result, dict):
            result['remark'] = self.remark or False
            result['is_wedding_order'] = self.is_wedding_order
            result['is_b2b_order'] = self.is_b2b_order
            # Auto-set dropship/dest address to the SO's delivery address.
            if self.partner_shipping_id:
                result['dest_address_id'] = self.partner_shipping_id.id
        return result

    def _action_confirm(self):
        """After confirm, propagate `remark` to the related stock pickings'
        `note` field on HangHeung-company SOs so the DN List Report's Remark
        column reflects 備註 from the upstream Hoymay SO."""
        result = super()._action_confirm()
        for order in self:
            if not order.remark:
                continue
            if order.company_id.id != 3:  # 3 = HangHeung Cake Shop Co.
                # Picking-note propagation is only for HangHeung's deliveries
                # (DN List report reads stock.picking.note for the Remark column).
                continue
            pickings = order.picking_ids
            if pickings:
                pickings.sudo().write({'note': order.remark})
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
