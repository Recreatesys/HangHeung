from odoo import models, fields, api, _
from odoo.osv import expression
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer = fields.Boolean(string='Customer', default=False, stored=True)
    vendor = fields.Boolean(string='Vendor', default=False, stored=True)
    is_internal_contact = fields.Boolean(
        string='Internal Contact',
        default=False, copy=False, index=True,
        help=(
            "When ticked, this partner is visible to every user role "
            "(POS, Sales, Purchase, Warehouse, Internal, Accounting). "
            "Used for the 4 entity-vendors that are also part of the "
            "company's own intercompany / key-vendor relationships."
        ),
    )
    contact_number = fields.Char(string='Contact No.', stored=True)
    alternative_contact_name = fields.Char(string='Alternative Name', stored=True)
    fax_number = fields.Char(string='Fax No.', stored=True)
    customer_credit_limit = fields.Integer(string='Credit Limit', default=0, stored=True)
    crdr_due_days = fields.Integer(string='CRDR Due Days', default=0, stored=True)
    customer_category_id = fields.Many2one(
        'customer.category', 
        string='Customer Category'
    )
    terms = fields.Char(string='Terms', stored=True)
    purchase_auto_confirm = fields.Boolean(string="Purchase Auto Confirm")
    has_moves = fields.Boolean(string="Has Moves")

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=100, order=None):
        """Extend customer/vendor name autocomplete to also match phone and mobile.

        Standard Odoo res.partner name_search already supports name/email/ref;
        we additionally OR-match phone and mobile so cashiers / sales staff
        can pull up a contact by typing the customer's phone digits.
        """
        if name and operator in ('ilike', '=', 'like', '=ilike', 'not ilike', 'not like'):
            base_domain = list(domain or [])
            extra = expression.OR([
                [('phone', operator, name)],
                [('mobile', operator, name)],
            ])
            try:
                std_ids = list(super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order))
            except Exception:
                std_ids = []
            extra_domain = expression.AND([base_domain, extra])
            extra_records = self.search(extra_domain, limit=limit, order=order)
            extra_ids = extra_records.ids
            combined = list(dict.fromkeys(std_ids + extra_ids))
            if limit:
                combined = combined[:limit]
            return combined
        return super()._name_search(name, domain=domain, operator=operator, limit=limit, order=order)

