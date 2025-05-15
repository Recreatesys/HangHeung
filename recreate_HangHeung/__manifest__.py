# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hang Heung Customizations',
    'version': '1.0',
    'summary': 'Includes all Hang Heung customizations',
    'description': """
        This module contains all of Hang Heung customizations.
    """,
    'author': 'Lau Siu Hin',
    'website': '',
    'depends': ['contacts', 'base', 'stock', 'web'],
    'data': [
        "views/res_partner.xml",
        "views/customer_category_data.xml",
        "security/ir.model.access.csv",
        "views/product_template.xml",
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
