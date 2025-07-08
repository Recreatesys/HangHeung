from odoo import models, fields, api, _
from datetime import datetime


class PosConfig(models.Model):
    _inherit = 'pos.config'

    current_session_id = fields.Many2one(
        'pos.session', compute='_compute_current_session_id', store=True)

    @api.depends('session_ids.state')
    def _compute_current_session_id(self):
        for config in self:
            session = config.session_ids.filtered(
                lambda s: s.state in ['opening_control', 'opened', 'closing_control'])[:1]
            config.current_session_id = session

            if session:
                config_name = config.name or 'POS'

                if ' - ' in config_name:
                    pos_code = config_name.split(' - ')[0].strip()
                else:
                    pos_code = config_name.strip()

                today_str = fields.Date.today().strftime('%Y%m%d')
                prefix = f'P{pos_code}-{today_str}'

                existing_sessions = self.env['pos.session'].search_count([('config_id','=',config.name)])
                count = existing_sessions
                session.name = f"{prefix}-{str(count).zfill(2)}"
