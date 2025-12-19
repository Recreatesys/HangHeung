from odoo import models, api

class RelocateStockQuant(models.TransientModel):
    _inherit = 'stock.quant.relocate'

    def action_relocate_quants(self):
        """
        Perform relocation using base Odoo logic,
        then assign POS store to loyalty coupons based on LOT.
        """

        self._assign_store_to_coupons()
        return super().action_relocate_quants()

    def _assign_store_to_coupons(self):
        self.ensure_one()
        if not self.dest_location_id:
            return

        pos_config = self.env['pos.config'].search([
            ('picking_type_id.default_location_src_id', '=', self.dest_location_id.id)
        ], limit=1)

        if not pos_config:
            return

        quant_ids = (
            self.env.context.get('default_quant_ids')
            or self.env.context.get('active_ids')
            or []
        )

        if not quant_ids:
            return

        self.env.cr.execute("""
            SELECT id
            FROM stock_quant
            WHERE id = ANY(%s)
        """, (quant_ids,))
        valid_quant_ids = [row[0] for row in self.env.cr.fetchall()]

        if not valid_quant_ids:
            return

        quants = self.env['stock.quant'].browse(valid_quant_ids)

        lots = quants.mapped('lot_id').filtered(bool)
        if not lots:
            return

        coupons = self.env['loyalty.card']
        for lot in lots:
            coupons |= self.env['loyalty.card'].search([
                ('code', '=', lot.name)
            ])

        if not coupons:
            return

        coupons.sudo().write({
            'allocated_store_id': pos_config.id
        })
