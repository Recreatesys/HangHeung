# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_omni_print = fields.Boolean(related='pos_config_id.use_omni_print', readonly=False)
    omni_print_enable_cashdrawer = fields.Boolean(related='pos_config_id.omni_print_enable_cashdrawer', readonly=False)

    @api.onchange('use_omni_print')
    def _onchange_use_omni_print(self):
        if not self.use_omni_print:
            self.omni_print_enable_cashdrawer = False

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.pos_config_id:
            self.pos_config_id.write({
                'use_omni_print': self.use_omni_print,
                'omni_print_enable_cashdrawer': self.omni_print_enable_cashdrawer,
            })