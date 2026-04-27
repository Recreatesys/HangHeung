# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Replace Date To Datetime',
    'version': '1.0.1',
    'summary': 'Replace Date To Datetime',
    'description': """
        Replace Date To Datetime.
    """,
    'author': 'Charles',
    'depends': ['pos_loyalty', 'loyalty',],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'replace_date_to_datetime/static/src/**/*'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
