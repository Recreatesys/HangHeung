# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import  fields, models


class ShResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_sh_pos_night_mode = fields.Boolean(related='pos_config_id.sh_pos_night_mode', readonly=False)
    refund_start_time = fields.Float(string="Start Time", related='pos_config_id.start_time', readonly=False)
    refund_end_time = fields.Float(string="End Time", related='pos_config_id.end_time', readonly=False)