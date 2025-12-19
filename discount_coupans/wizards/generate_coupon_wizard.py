from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GenerateCouponWizard(models.TransientModel):
    _name = "generate.coupon.wizard"
    _description = "Generate / Sell Coupons Wizard"

    order_id = fields.Many2one('sale.order', readonly=True)
    order_line_id = fields.Many2one('sale.order.line', readonly=True)
    product_id = fields.Many2one('product.product', readonly=True)

    coupon_action = fields.Selection([
        ('generate', 'Generate New Coupons'),
        ('sell', 'Sell Existing Coupons'),
    ], default='generate', required=True)

    prefix = fields.Char(default="CHR")
    from_number = fields.Char()
    range_count = fields.Char()
    to_number = fields.Char(readonly=True)

    store_id = fields.Many2one('pos.config')

    available_coupon_ids = fields.Many2many(
        'loyalty.card',
        compute='_compute_available_coupons',
        string="Available Coupons"
    )

    selected_coupon_ids = fields.Many2many(
        'loyalty.card',
        string="Select Coupons to Sell"
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        line_id = self._context.get('default_order_line_id')
        if not line_id:
            raise ValidationError(_("Open this wizard from Sale Order Line."))

        line = self.env['sale.order.line'].browse(line_id)

        if not line.product_id.is_coupon or not line.product_id.loyalty_program_id:
            raise ValidationError(_("Selected product is not a coupon product."))

        res.update({
            'order_id': line.order_id.id,
            'order_line_id': line.id,
            'product_id': line.product_id.id,
        })
        return res

    @api.depends('coupon_action', 'product_id')
    def _compute_available_coupons(self):
        for wizard in self:
            if wizard.coupon_action != 'sell' or not wizard.product_id:
                wizard.available_coupon_ids = False
                continue

            wizard.available_coupon_ids = self.env['loyalty.card'].search([('program_id', '=', wizard.product_id.loyalty_program_id.id),
                                                                           ('status', '=', 'not_activated'),
                                                                           ('lot_id', '!=', False),])

    @api.onchange('from_number', 'range_count')
    def _onchange_auto_to(self):
        if self.from_number and self.range_count \
           and self.from_number.isdigit() and self.range_count.isdigit():

            start = int(self.from_number)
            qty = int(self.range_count)
            if qty > 0:
                self.to_number = str(start + qty - 1).zfill(len(self.from_number))

    def _validate_quantity(self, qty):
        if qty > self.order_line_id.product_uom_qty:
            raise ValidationError(_("Selected coupon quantity exceeds order line quantity."))

    def _validate_duplicates(self, codes):
        if self.env['loyalty.card'].search([('code', 'in', codes)], limit=1):
            raise ValidationError(_("Some coupon codes already exist."))

    def _generate_new_coupons(self):
        start = int(self.from_number)
        qty = int(self.range_count)

        if qty > self.order_line_id.product_uom_qty:
            raise ValidationError(_("Coupon quantity exceeds order quantity."))

        padding = len(self.from_number)
        location = self.order_id.warehouse_id.lot_stock_id

        created_coupons = self.env['loyalty.card']

        for i in range(start, start + qty):
            code = f"{self.prefix}{str(i).zfill(padding)}"

            lot = self.env['stock.lot'].create({
                'name': code,
                'product_id': self.product_id.id,
            })

            self.env['stock.quant'].create({
                'product_id': self.product_id.id,
                'location_id': location.id,
                'lot_id': lot.id,
                'quantity': 1,
            })

            created_coupons |= self.env['loyalty.card'].create({
                'code': code,
                'prefix': self.prefix,
                'program_id': self.product_id.loyalty_program_id.id,
                'status': 'not_activated',
                'lot_id': lot.id,
            })
        self.order_line_id.reserved_coupon_ids = [(6, 0, created_coupons.ids)]

    def _sell_existing_coupons(self):
        coupons = self.selected_coupon_ids
        if not coupons:
            raise ValidationError(_("Please select coupons to sell."))

        if len(coupons) > self.order_line_id.product_uom_qty:
            raise ValidationError(_("Selected coupons exceed order quantity."))

        self.order_line_id.reserved_coupon_ids = [(6, 0, coupons.ids)]

    def _assign_lots_to_delivery(self, lots=None, limit=0):
        picking = self.order_id.picking_ids.filtered(lambda p: p.state not in ('cancel'))[:1]
        if not picking:
            return

        picking.action_assign()
        move = picking.move_ids.filtered(lambda m: m.product_id == self.product_id)[:1]
        if not move:
            return

        if not lots:
            lots = self.env['stock.lot'].search(
                [('product_id', '=', self.product_id.id)],
                order='id desc',
                limit=limit
            )

        for lot in lots:
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': self.product_id.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'lot_id': lot.id,
                'qty_done': 1,
            })

    def action_generate(self):
        self.ensure_one()

        if self.coupon_action == 'generate':
            self._generate_new_coupons()
        else:
            self._sell_existing_coupons()

        self.order_id.message_post(
            body=_("Coupons processed for %s") % self.product_id.display_name
        )

        return {'type': 'ir.actions.act_window_close'}
