# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.

from odoo import models, api


class PosSessionInherit(models.Model):
    _inherit = "pos.session"

    def _loader_params_product_product(self):
        result = super(PosSessionInherit,
                       self)._loader_params_product_product()
        result['search_params']['fields'].extend(
            ["type", "qty_available", "virtual_available"])
        return result

    @api.model
    def _load_pos_data_models(self, config_id):
        data_models = super()._load_pos_data_models(config_id)
        data_models += ['sh.pos.theme.settings']
        return data_models
