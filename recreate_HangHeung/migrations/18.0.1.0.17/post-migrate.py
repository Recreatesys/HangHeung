import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


# Hard-coded canonical entity IDs (verified on prod 2026-04-30).
# 1     -> Hoymay HK Ltd
# 7280  -> 太古可口可樂有限公司 OPT-000072
# 8883  -> That's Ltd
# 8884  -> HANG HEUNG CAKE SHOP COMPANY LIMITED
INTERNAL_CONTACT_PARTNER_IDS = (1, 7280, 8883, 8884)

# Old ir.rule ids that the new role-bound rules in role_groups.xml supersede.
# Deactivated, not deleted, so they can be revived if a regression appears.
DEACTIVATE_RULE_IDS = (293, 294, 298, 299, 331, 332, 333)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Flag the 4 entity-vendors as Internal Contact.
    Partner = env['res.partner'].sudo()
    targets = Partner.browse(INTERNAL_CONTACT_PARTNER_IDS).exists()
    if targets:
        # Filter to those not already flagged so we don't churn write_date
        not_yet = targets.filtered(lambda p: not p.is_internal_contact)
        if not_yet:
            not_yet.write({'is_internal_contact': True})
            _logger.info(
                "is_internal_contact=True set on %d entity partner(s): %s",
                len(not_yet), not_yet.mapped(lambda p: '%s(%d)' % (p.name, p.id)),
            )
    missing = set(INTERNAL_CONTACT_PARTNER_IDS) - set(targets.ids)
    if missing:
        _logger.warning(
            "Internal Contact migration: partners not found on this DB: %s",
            sorted(missing),
        )

    # 2) Deactivate superseded ir.rules. The new role-bound rules live in
    #    security/role_groups.xml; the old global rules conflict with the
    #    OR-semantics across roles.
    Rule = env['ir.rule'].sudo()
    rules = Rule.browse(DEACTIVATE_RULE_IDS).exists()
    if rules:
        active = rules.filtered('active')
        if active:
            active.write({'active': False})
            _logger.info(
                "Deactivated %d superseded ir.rule record(s): %s",
                len(active), active.mapped('name'),
            )
    missing_rules = set(DEACTIVATE_RULE_IDS) - set(rules.ids)
    if missing_rules:
        _logger.info(
            "Deactivate-rules migration: rule ids not present on this DB (skipped): %s",
            sorted(missing_rules),
        )
