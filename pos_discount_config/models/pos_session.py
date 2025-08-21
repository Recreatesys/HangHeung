from odoo import models, fields, api

class PosSessionInherit(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['discount.config']
        return data

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        return data