from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import float_compare, groupby
import logging

_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    @api.model
    def _default_picking_type(self):
        curr_company = self.env.context.get('allowed_company_ids')[0]
        if curr_company == 2:
            return self.env['stock.picking.type'].search([('code', '=', 'dropship'), ('company_id', '=', 2)], limit=1).id
        elif curr_company == 1:
            return self.env['res.users'].search([('id', '=', self.env.user.id)]).default_receipt_type
    

    @api.model
    def _default_dest_address(self):
        return self.env['res.users'].search([('id', '=', self.env.user.id)]).default_dest_address


    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        change_default=True,
        tracking=True,
        check_company=True,
        default=lambda self: self.get_default_vendor(),
        help="You can find a vendor by its Name, TIN, Email or Internal Reference."
    )

    picking_type_id = fields.Many2one(
        'stock.picking.type', 
        'Deliver To', 
        required=False, 
        default=_default_picking_type,
        domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]",
        help="This will determine operation type of incoming shipment"
    )

    dest_address_id = fields.Many2one('res.partner', store=True, readonly=False, default=_default_dest_address)


    @api.onchange('picking_type_id')
    def onchange_dest_address_id(self):
        for purchase_order in self:
            purchase_order.dest_address_id = purchase_order.picking_type_id.warehouse_id.partner_id.id


    def copy(self, default=None):
        res = super(PurchaseOrder,self).copy(default=default)
        if self.partner_id.purchase_auto_confirm:
            self.button_confirm()
        return res


    @api.model
    def get_default_vendor(self):
        partner = False
        curr_company = self.env.context.get("allowed_company_ids")[0]
        if curr_company == 1:
            partner = self.env['res.partner'].search([('id', '=', 8883)], limit=1)
        elif curr_company == 2:
            partner = self.env['res.partner'].search([('name', '=', 'Hang Heung Cake Shop Company Limited')], limit=1)
        return partner.id if partner else False
    

    @api.onchange('company_id')
    def _onchange_company_id(self):
        pass

    

class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _run_buy(self, procurements):
        procurements_by_po_domain = defaultdict(list)
        errors = []
        for procurement, rule in procurements:

            # Get the schedule date in order to find a valid seller
            procurement_date_planned = fields.Datetime.from_string(procurement.values['date_planned'])

            supplier = False
            company_id = rule.company_id or procurement.company_id
            if procurement.values.get('supplierinfo_id'):
                supplier = procurement.values['supplierinfo_id']
            elif procurement.values.get('orderpoint_id') and procurement.values['orderpoint_id'].supplier_id:
                supplier = procurement.values['orderpoint_id'].supplier_id
            else:
                supplier = procurement.product_id.with_company(company_id.id)._select_seller(
                    partner_id=self._get_partner_id(procurement.values, rule),
                    quantity=procurement.product_qty,
                    date=max(procurement_date_planned.date(), fields.Date.today()),
                    uom_id=procurement.product_uom)

            # Fall back on a supplier for which no price may be defined. Not ideal, but better than
            # blocking the user.
            supplier = supplier or procurement.product_id._prepare_sellers(False).filtered(
                lambda s: not s.company_id or s.company_id == company_id
            )[:1]

            if not supplier:
                msg = _('There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.', procurement.product_id.display_name)
                errors.append((procurement, msg))

            partner = supplier.partner_id
            # we put `supplier_info` in values for extensibility purposes
            procurement.values['supplier'] = supplier
            procurement.values['propagate_cancel'] = rule.propagate_cancel

            domain = rule._make_po_get_domain(company_id, procurement.values, partner)
            procurements_by_po_domain[domain].append((procurement, rule))

        if errors:
            raise ProcurementException(errors)
        

        for domain, procurements_rules in procurements_by_po_domain.items():
            # Get the procurements for the current domain.
            # Get the rules for the current domain. Their only use is to create
            # the PO if it does not exist.
            procurements, rules = zip(*procurements_rules)

            # Get the set of procurement origin for the current domain.
            origins = set([p.origin for p in procurements if p.origin])
            # Check if a PO exists for the current domain.
            po = self.env['purchase.order'].sudo().search([dom for dom in domain], limit=1)
            company_id = rules[0].company_id or procurements[0].company_id
            if not po:
                positive_values = [p.values for p in procurements if float_compare(p.product_qty, 0.0, precision_rounding=p.product_uom.rounding) >= 0]
                if positive_values:
                    # We need a rule to generate the PO. However the rule generated
                    # the same domain for PO and the _prepare_purchase_order method
                    # should only uses the common rules's fields.
                    vals = rules[0]._prepare_purchase_order(company_id, origins, positive_values)
                    po_origin = self.env['purchase.order'].search([('company_id', '=', 1), ('partner_ref', '=', vals['origin'])])
                    # The company_id is the same for all procurements since
                    # _make_po_get_domain add the company in the domain.
                    # We use SUPERUSER_ID since we don't want the current user to be follower of the PO.
                    # Indeed, the current user may be a user without access to Purchase, or even be a portal user.
                    if vals['company_id'] == 2:
                        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'dropship'), ('company_id', '=', 2)], limit=1).id
                        if not po_origin:
                            dest_address = self.env['res.users'].search([('id', '=', self.env.context['uid'])]).default_dest_address.id
                        else:
                            dest_address = po_origin.dest_address_id.id
                        if picking_type_id:
                            vals['picking_type_id'] = picking_type_id
                        if dest_address:
                            vals['dest_address_id'] = dest_address
                    po = self.env['purchase.order'].with_company(company_id).with_user(SUPERUSER_ID).create(vals)
            else:
                # If a purchase order is found, adapt its `origin` field.
                if po.origin:
                    missing_origins = origins - set(po.origin.split(', '))
                    if missing_origins:
                        po.write({'origin': po.origin + ', ' + ', '.join(missing_origins)})
                else:
                    po.write({'origin': ', '.join(origins)})
                if po.company_id.id == 2:
                    picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'dropship'), ('company_id', '=', 2)], limit=1).id
                    dest_address = self.env['res.users'].search([('id', '=', self.env.context['uid'])]).default_dest_address.id
                    po.write({'picking_type_id': picking_type_id, 'dest_address_id': dest_address})

            procurements_to_merge = self._get_procurements_to_merge(procurements)
            procurements = self._merge_procurements(procurements_to_merge)

            po_lines_by_product = {}
            grouped_po_lines = groupby(po.order_line.filtered(lambda l: not l.display_type and l.product_uom == l.product_id.uom_po_id), key=lambda l: l.product_id.id)
            for product, po_lines in grouped_po_lines:
                po_lines_by_product[product] = self.env['purchase.order.line'].concat(*po_lines)
            po_line_values = []
            for procurement in procurements:
                po_lines = po_lines_by_product.get(procurement.product_id.id, self.env['purchase.order.line'])
                po_line = po_lines._find_candidate(*procurement)

                if po_line:
                    # If the procurement can be merge in an existing line. Directly
                    # write the new values on it.
                    vals = self._update_purchase_order_line(procurement.product_id,
                        procurement.product_qty, procurement.product_uom, company_id,
                        procurement.values, po_line)
                    po_line.sudo().write(vals)
                else:
                    if float_compare(procurement.product_qty, 0, precision_rounding=procurement.product_uom.rounding) <= 0:
                        # If procurement contains negative quantity, don't create a new line that would contain negative qty
                        continue
                    # If it does not exist a PO line for current procurement.
                    # Generate the create values for it and add it to a list in
                    # order to create it in batch.
                    partner = procurement.values['supplier'].partner_id
                    po_line_values.append(self.env['purchase.order.line']._prepare_purchase_order_line_from_procurement(
                        *procurement, po))
                    # Check if we need to advance the order date for the new line
                    order_date_planned = procurement.values['date_planned'] - relativedelta(
                        days=procurement.values['supplier'].delay)
                    if fields.Date.to_date(order_date_planned) < fields.Date.to_date(po.date_order):
                        po.date_order = order_date_planned
            self.env['purchase.order.line'].sudo().create(po_line_values)
            if po.partner_id.purchase_auto_confirm:
                po.button_confirm()
        