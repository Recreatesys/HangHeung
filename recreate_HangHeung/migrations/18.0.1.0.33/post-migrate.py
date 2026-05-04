import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


# Idempotent: flag the umbrella parent for the 19 HH internal retail outlets
# (created out-of-band in 2026-05; partner id differs per DB so we look up by
# name). Without this flag, the POS-User ir.rule on res.partner hides the
# shop partners themselves -- breaking PO confirmation for shop users when
# the PO's dest_address_id points at the shop.
INTERNAL_SHOPS_PARENT_NAME = 'HangHeung Internal Shops'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    Partner = env['res.partner'].sudo()
    parent = Partner.search([
        ('name', '=', INTERNAL_SHOPS_PARENT_NAME),
        ('is_company', '=', True),
    ], limit=1)
    if not parent:
        _logger.info(
            "%s partner not present on this DB; skipping is_internal_contact flag.",
            INTERNAL_SHOPS_PARENT_NAME,
        )
        return
    if not parent.is_internal_contact:
        parent.write({'is_internal_contact': True})
        _logger.info(
            "is_internal_contact=True set on '%s' (id=%d).",
            parent.name, parent.id,
        )
