from odoo import models, api, fields,_
from datetime import datetime
from collections import defaultdict
from odoo.osv.expression import AND
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz

class PosOrder(models.Model):
    _inherit = 'pos.order'
    
    def _check_refund_time_window(self):
        for order in self:
            config = order.config_id
            if config.start_time and config.end_time:
                user = self.env.user
                user_tz = user.tz or 'UTC'
                local_tz = pytz.timezone(user_tz)

                now_utc = datetime.utcnow()
                now_local = now_utc.astimezone(local_tz)
                
                current_time = now_local.hour + now_local.minute / 60.0

                if not (config.start_time <= current_time <= config.end_time):
                    raise UserError(_(
                        "Refund or cancellation is only allowed between %.2f and %.2f (your local time: %s)"
                    ) % (config.start_time, config.end_time, now_local.strftime('%H:%M')))
            else:
                raise UserError(_("Refund or cancellation time window is not set for this POS configuration.")) 

    def refund(self):
        self._check_refund_time_window()
        return super().refund()

    def action_pos_order_cancel(self):
        self._check_refund_time_window()
        return super().action_pos_order_cancel()
