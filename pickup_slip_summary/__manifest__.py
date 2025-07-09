# -*- coding: utf-8 -*-
{
    'name': 'Pickup Slip Summary Report',
    'version': '18.0.1.0.0',
    'summary': """Pickup Slip Summary Report""",
    'category': 'Reporting',
    'description': """This module provides a report for Pickup Slip Summary in Odoo.""",
    'depends': ['base',],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
        'wizard/operation_wizard_views.xml'
    ],
    'demo': [
    ],
  
    'installable': True,
    'application': True,
}
