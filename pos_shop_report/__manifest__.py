# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Hang Heung Shop Reports Customizations',
    'version': '1.0',
    'summary': 'Includes all Hang Heung customizations',
    'description': """
        This module contains all of Hang Heung customizations.
    """,
    'author': 'Lau Siu Hin',
    'website': '',
    'depends': ['contacts', 'base', 'stock', 'web', 'purchase'],
    'data': [
        "security/ir.model.access.csv",
        "wizards/pos_shop_report_wizard.xml",
        "views/pos_shop_report.xml",
        "reports/pos_shop_report.xml",
        "reports/pos_shop_report_format.xml"
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}
