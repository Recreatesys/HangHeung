# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

{
    "name": "Point Of Sale Extended Receipt",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "point of sale",
    "summary": "Point Of Sale Receipt POS Customizable Receipt Custom Receipt Barcode On Receipt QRCode On Receipt POS Invoice Number On Receipt QRCode Receipt Barcode Receipt Invoice Number On POS Receipt Invoice on Receipt POS Invoice Receipt Invoice Number In POS",
    "description": """This POS module allows you to customize the receipt as per your choice. You can display Barcode or QRCode, invoice number & customer details(name, address, mobile number, phone number & email) in the POS order receipt.""",
    "version": "0.0.4",
    "depends": ["base", "web", "point_of_sale"],
    "data": [
        'views/res_config_setting.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'sh_pos_receipt_extend/static/src/**/*',
            ],
    },
    "auto_install": False,
    "installable": True,
    "license": "OPL-1",
    "application": True,
    "images": ["static/description/background.png", ],
    "price": 20,
    "currency": "EUR"
}
