{
    "name": "Discount Coupons",
    "version": "1.0",
    "summary": "Manage discount coupons and apply them to sales",
    "description": "This module allows you to create, manage, and apply discount coupons in sales and POS.",
    "author": "CodeTrade India Pvt.Ltd.",
    "website": "https://www.codetrade.io",
    "depends": ["sale", "base", "point_of_sale","loyalty","pos_loyalty","replace_date_to_datetime","sale_loyalty"],
    "data": [
        "security/ir.model.access.csv",
        "views/loyalty_card_views.xml",
        "views/product_template.xml",
        "wizards/loyalty_genarate_wizard.xml",
        "wizards/excel_report_views.xml",
    ],
    "assets": {
        "point_of_sale.assets": [
            "discount_coupans/static/src/js/pos_store.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
