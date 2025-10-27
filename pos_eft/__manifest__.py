{
    "name": "EFT Provider",
    "version": "1.0",
    
    "summary": "Manage payment transactions with EFT providers",
    "description": "This module allows you to manage payment transactions with EFT providers",
    "author": "CodeTrade India Pvt.Ltd.",
    "website": "https://www.codetrade.io",
    "depends": ["payment","base","point_of_sale"],
    "data": [
        "data/eft.xml",
        "views/provider.xml",
        "views/eft_provider.xml",
        "views/pos_payment_method_views.xml",
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            "pos_eft/static/src/js/eft_payment.js",
            "pos_eft/static/src/js/pos_payment.js",
            "pos_eft/static/src/xml/qr_code.xml",
            "pos_eft/static/src/js/pos_customer_filter.js",
            "pos_eft/static/src/js/eft_payment_interface.js"
        ],
    },
    
    "installable": True,
    "application": False,
    "auto_install": False,
}