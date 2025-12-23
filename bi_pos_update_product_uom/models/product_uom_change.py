# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, api, _, tools



import random

from odoo.addons.stock.models.product import ProductTemplate

from odoo.tools import float_is_zero
import json
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict



class UoM(models.Model):
	_inherit = 'uom.uom'

	def _compute_quantity(self, qty, to_unit, round=True, rounding_method='UP', raise_if_failure=True):
		if not self or not qty:
			return qty
		self.ensure_one()

		if self != to_unit and self.category_id.id != to_unit.category_id.id:
			return qty

		if self == to_unit:
			amount = qty
		else:
			amount = qty / self.factor
			if to_unit:
				amount = amount * to_unit.factor

		if to_unit and round:
			amount = tools.float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)

		return amount



class ProductTemplates(models.Model):
	_inherit = 'product.template'


	@api.constrains('uom_id')
	def _check_uom_not_in_invoice(self):
		for template in self:
			invoices = self.env['account.move.line'].sudo().search([('product_id.product_tmpl_id.id', '=', template.id)], limit=1)

		
	def write(self, vals):

		for rec in self:
			if 'uom_id' in vals:
				new_uom = self.env['uom.uom'].browse(vals['uom_id'])
				updated = self.filtered(lambda template: template.uom_id != new_uom)
			if rec.nbr_reordering_rules:
				if 'type' in vals and vals['type'] != 'product' and sum(rec.mapped('nbr_reordering_rules')) != 0:
					raise UserError(_('You still have some active reordering rules on this product. Please archive or delete them first.'))
			if rec.product_variant_ids:				
				if any('type' in vals and vals['type'] != prod_tmpl.type for prod_tmpl in self):
					existing_move_lines = self.env['stock.move.line'].search([
						('product_id', 'in', rec.mapped('product_variant_ids').ids),
						('state', 'in', ['partially_available', 'assigned']),
					])
					if existing_move_lines:
						raise UserError(_("You can not change the type of a product that is currently reserved on a stock move. If you need to change the type, you should first unreserve the stock move."))
			if 'type' in vals and vals['type'] != 'product' and any(p.type == 'product' and not float_is_zero(p.qty_available, precision_rounding=p.uom_id.rounding) for p in self):
				raise UserError(_("Available quantity should be set to zero before changing type"))
		
		return super(ProductTemplate, self).write(vals)

