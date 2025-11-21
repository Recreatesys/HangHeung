from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GenerateCouponWizard(models.TransientModel):
    _name = "generate.coupon.wizard"
    _description = "Generate Coupons Wizard"

    order_id = fields.Many2one('sale.order', string="Order", readonly=True)
    product_id = fields.Many2one('product.product', string="Coupon Product", required=True)
    prefix = fields.Char(string="Prefix", required=True, default="CHR")

    from_number = fields.Char(string="Range From", required=True)
    range_count = fields.Char(string="Range", required=True)
    to_number = fields.Char(string="Range To", readonly=True, store=True)

    store_id = fields.Many2one('pos.config', string="Allocated Store")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        order = self.env['sale.order'].browse(self._context.get('default_order_id'))

        coupon_products = order.order_line.filtered(
            lambda l: l.product_id.is_coupon and l.product_id.loyalty_program_id
        ).mapped('product_id')

        if not coupon_products:
            raise ValidationError("No coupon product found in this Sale Order.")

        if len(coupon_products) > 1:
            raise ValidationError("Multiple coupon products found — keep only one coupon product per sale order.")

        res['product_id'] = coupon_products[0].id
        res['order_id'] = order.id if order else False

        return res


    @api.onchange('from_number', 'range_count')
    def _onchange_auto_to(self):
        if self.from_number and self.range_count:

            if not (self.from_number.isdigit() and self.range_count.isdigit()):
                self.to_number = ""
                return

            start = int(self.from_number)
            qty = int(self.range_count)

            if qty <= 0:
                self.to_number = ""
                return

            end = start + qty - 1
            padding = len(self.from_number)
            self.to_number = str(end).zfill(padding)

    def _validate_duplicates(self):
        start = int(self.from_number)
        end = int(self.to_number)
        padding = len(self.from_number)

        codes = [f"{self.prefix}{str(i).zfill(padding)}" for i in range(start, end + 1)]

        existing_cards = self.env['loyalty.card'].search([('code', 'in', codes)])
        if existing_cards:
            raise ValidationError(_("These coupon codes already exist: %s") %
                                  ", ".join(existing_cards.mapped('code')))

        existing_lots = self.env['stock.lot'].search([('name', 'in', codes)])
        if existing_lots:
            raise ValidationError(_("These LOT numbers already exist: %s") %
                                  ", ".join(existing_lots.mapped('name')))
    def _assign_lots_to_delivery(self):

        pickings = self.order_id.picking_ids.filtered(lambda p: p.state not in ('cancel'))

        start = int(self.from_number)
        end = int(self.to_number)
        padding = len(self.from_number)

        lots = self.env['stock.lot'].search([
            ('name', '>=', f"{self.prefix}{str(start).zfill(padding)}"),
            ('name', '<=', f"{self.prefix}{str(end).zfill(padding)}"),
            ('product_id', '=', self.product_id.id),
        ], order="name asc")

        lot_index = 0

        for picking in pickings:

            picking.action_assign()

            for move in picking.move_ids.filtered(lambda m: m.product_id == self.product_id):

                remaining_qty = move.product_uom_qty

                while remaining_qty > 0 and lot_index < len(lots):

                    lot = lots[lot_index]

                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': self.product_id.id,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'lot_id': lot.id,
                        'qty_done': 1,
                    })

                    remaining_qty -= 1
                    lot_index += 1


    def action_generate(self):
        self.ensure_one()

        self._validate_duplicates()

        LoyaltyCard = self.env['loyalty.card']
        Lot = self.env['stock.lot']
        Quant = self.env['stock.quant']

        start = int(self.from_number)
        end = int(self.to_number)
        padding = len(self.from_number)

        total = end - start + 1

        so_line = self.order_id.order_line.filtered(lambda l: l.product_id == self.product_id)
        if not so_line:
            raise ValidationError(_("Coupon product not found in sale order lines."))

        qty_in_order = so_line.product_uom_qty

        if total > qty_in_order:
            raise ValidationError(
                _("You cannot generate %s coupons because sale order only contains %s quantity.")
                % (total, qty_in_order)
            )

        warehouse = (
            self.product_id.store_id.picking_type_id.warehouse_id or
            self.env['stock.warehouse'].search(
                [('company_id', '=', self.order_id.company_id.id)], limit=1
            )
        )

        location = warehouse.lot_stock_id

        for i in range(start, end + 1):

            number = str(i).zfill(padding)
            code = f"{self.prefix}{number}"

            lot = Lot.create({
                'name': code,
                'product_id': self.product_id.id,
            })

            Quant.create({
                'product_id': self.product_id.id,
                'location_id': location.id,
                'quantity': 1,
                'lot_id': lot.id,
            })

            LoyaltyCard.create({
                'prefix': self.prefix,
                'range_from': number,
                'range_to': number,
                'allocated_store_id': self.store_id.id,
                'code': code,
                'status': 'not_activated',
                'program_id': self.product_id.loyalty_program_id.id,
                'lot_id': lot.id,
            })

        self.order_id.message_post(body=f"{total} coupons generated manually using wizard.")


        self._assign_lots_to_delivery()

        self.order_id.final_confirm_after_coupon()

        return {'type': 'ir.actions.act_window_close'}
