from odoo import models, api, fields

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        params = super()._loader_params_product_product()
        
        search_params = params.get('search_params', {})
        if 'fields' in search_params and 'type' not in search_params['fields']:
            search_params['fields'].append('type')
        return params
    
    @api.model
    def check_low_stock(self, session_id, needs_map):
        """
        Only check if product exists in POS stock location.
        Returns available stock for each product.
        """
        session = self.browse(session_id).sudo()
        config = session.config_id

        loc_id = (
            config.picking_type_id.warehouse_id.lot_stock_id.id
            if (
                config.picking_type_id
                and config.picking_type_id.warehouse_id
                and config.picking_type_id.warehouse_id.lot_stock_id
            )
            else (config.stock_location_id.id if config.stock_location_id else False)
        )

        if not loc_id or not needs_map:
            return []

        ProductCtx = (
            self.env["product.product"]
            .with_company(config.company_id)
            .with_context(location=loc_id, compute_child=False)
        )

        results = []

        for pid in (needs_map or {}):
            prod = ProductCtx.browse(int(pid)).exists()
            if not prod:
                continue

            prod_loc = prod.with_context(location=loc_id, compute_child=False)
            available = float(prod_loc.qty_available)

            results.append({
                "product_id": prod.id,
                "display_name": prod.display_name,
                "available": available,
            })

        return results
