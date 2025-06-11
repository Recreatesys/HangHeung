# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = "pos.config"

    use_omni_print = fields.Boolean(string="Omni Print", compute="_compute_use_omni_print", readonly=False, store=True, help="Send the print job to Omni Print")
    omni_print_enable_cashdrawer = fields.Boolean(string="Cash Drawer")

    @api.depends('is_posbox', 'other_devices')
    def _compute_use_omni_print(self):
        for config in self:
            if config.is_posbox or config.other_devices:
                config.use_omni_print = False
