# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Negative Payment Validation",
    "version": "0.0.3",
    "category": "Point Of Sale",
    "sequence": 1,
    "license": "OPL-1",
    "summary": "Validates and prevents negative payments in the Odoo POS system with a modern, responsive theme.",
    "description": """This module validates and prevents negative payments in the Odoo Point of Sale system, ensuring that payment amounts cannot be less than zero.""",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com/",
    "depends": ["point_of_sale"],
    'assets': { 'point_of_sale._assets_pos': [
            'negative_payment_validation/static/src/overrides/**/*',
            ],
        },
    "support": "support@softhealer.com",
    "installable": True,
    "auto_install": False,
    "currency": "EUR",
}

