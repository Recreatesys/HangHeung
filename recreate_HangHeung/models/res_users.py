from odoo import models, fields, api, _
from datetime import datetime
import logging
from odoo.exceptions import ValidationError
import re

_logger = logging.getLogger(__name__)


# Order matters: when computing the role for an existing user, the FIRST
# matching group (highest precedence) wins. Most-permissive at the top.
PARTNER_ACCESS_ROLE_GROUPS = (
    ('accounting_user', 'recreate_HangHeung.group_accounting_user'),
    ('warehouse_clerk', 'recreate_HangHeung.group_warehouse_clerk'),
    ('purchase_user',   'recreate_HangHeung.group_non_sales_user'),
    ('sales_user',      'recreate_HangHeung.group_sales_user'),
    ('pos_user',        'recreate_HangHeung.group_pos_user'),
    ('internal_user',   'recreate_HangHeung.group_internal_user_only'),
)


class ResUsers(models.Model):
    _inherit = 'res.users'

    default_receipt_type = fields.Many2one(comodel_name="stock.picking.type", string="Default Receipt", store=True,  domain="['|', ('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id), ('name', '=', 'Receipts')]")
    default_dest_address = fields.Many2one(comodel_name="res.partner", string="Default Address", store=True)

    partner_access_role = fields.Selection(
        [
            ('pos_user',        'POS User'),
            ('sales_user',      'Sales User'),
            ('purchase_user',   'Purchase User'),
            ('warehouse_clerk', 'Warehouse Clerk'),
            ('internal_user',   'Internal User'),
            ('accounting_user', 'Accounting User'),
        ],
        string='Partner Access Role',
        compute='_compute_partner_access_role',
        inverse='_inverse_partner_access_role',
        store=True,
        help=(
            "Display-only summary of the user's partner-visibility role. "
            "Setting this value ADDS the user to the matching role group "
            "(does not strip existing memberships). Users may belong to "
            "multiple role groups; access is granted as the union (OR) "
            "across all groups."
        ),
    )

    def _resolve_role_group_id(self, xmlid):
        return self.env.ref(xmlid, raise_if_not_found=False)

    @api.depends('groups_id')
    def _compute_partner_access_role(self):
        for user in self:
            picked = False
            for value, xmlid in PARTNER_ACCESS_ROLE_GROUPS:
                grp = user._resolve_role_group_id(xmlid)
                if grp and grp in user.groups_id:
                    user.partner_access_role = value
                    picked = True
                    break
            if not picked:
                user.partner_access_role = False

    def _inverse_partner_access_role(self):
        for user in self:
            target_value = user.partner_access_role
            if not target_value:
                continue
            xmlid = dict(PARTNER_ACCESS_ROLE_GROUPS).get(target_value)
            if not xmlid:
                continue
            grp = user._resolve_role_group_id(xmlid)
            if not grp:
                _logger.warning(
                    "partner_access_role inverse: group '%s' not found; skipping for user %s",
                    xmlid, user.login,
                )
                continue
            if grp not in user.groups_id:
                user.groups_id = [(4, grp.id)]
