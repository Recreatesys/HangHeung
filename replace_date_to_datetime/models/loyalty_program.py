from odoo.exceptions import UserError
from odoo import api, fields, models, _

class LoyaltyProgram(models.Model):
    _inherit = 'loyalty.program'

    date_from = fields.Datetime(
        string="Start Date",
        help="The start date is included in the validity period of this program",
    )
    date_to = fields.Datetime(
        string="End date",
        help="The end date is included in the validity period of this program",
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_from_date_to(self):
        if any(p.date_to and p.date_from and fields.Date.to_date(p.date_from) > fields.Date.to_date(p.date_to) for p in self):
            raise UserError(_(
                "The validity period's start date must be anterior or equal to its end date."
            ))