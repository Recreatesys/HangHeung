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

        Bom = self.env['mrp.bom'].sudo() if 'mrp.bom' in self.env else None

        for pid in (needs_map or {}):
            prod = ProductCtx.browse(int(pid)).exists()
            if not prod:
                continue

            # HH-CUSTOM: combo products have no own stock -- their real
            # availability is on the choices. Treat them as effectively
            # unlimited so the cashier can open the combo popup; the
            # individual choices' stock is checked when each is added.
            if prod.product_tmpl_id.type == 'combo':
                results.append({
                    "product_id": prod.id,
                    "display_name": prod.display_name,
                    "available": 1e9,
                })
                continue

            # HH-CUSTOM: phantom-BOM kits also report qty_available = 0.
            # Compute effective availability as floor(min(component_stock
            # / component_qty)) across the BOM lines so the cashier sees
            # the real number of kits sellable from current components.
            if Bom is not None:
                phantom = Bom.search([
                    '|',
                    ('product_id', '=', prod.id),
                    '&', ('product_tmpl_id', '=', prod.product_tmpl_id.id), ('product_id', '=', False),
                    ('type', '=', 'phantom'),
                ], limit=1)
                if phantom:
                    kit_avail = None
                    for line in phantom.bom_line_ids:
                        comp = line.product_id.with_context(location=loc_id, compute_child=False)
                        per_kit = line.product_qty or 1.0
                        n = int(comp.qty_available // per_kit)
                        kit_avail = n if kit_avail is None else min(kit_avail, n)
                    results.append({
                        "product_id": prod.id,
                        "display_name": prod.display_name,
                        "available": float(kit_avail or 0),
                    })
                    continue

            prod_loc = prod.with_context(location=loc_id, compute_child=False)
            available = float(prod_loc.qty_available)

            results.append({
                "product_id": prod.id,
                "display_name": prod.display_name,
                "available": available,
            })

        return results
