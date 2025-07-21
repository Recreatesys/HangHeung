# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models

class ShPosConfig(models.Model):
    _inherit = 'pos.config'

    sh_pos_night_mode = fields.Boolean(string="Enable Night Mode")
    start_time = fields.Float(string="Start Time", help="Time after which refunds can start (e.g., 14.5 = 2:30 PM)", required=True)
    end_time = fields.Float(string="End Time", help="Time before which refunds must be completed (e.g., 17.0 = 5:00 PM)", required=True)
