from odoo import models, fields, api

class InheritResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super(InheritResPartner, self)._load_pos_data_fields(config_id) + [
            'customer',
            'vendor'
        ]