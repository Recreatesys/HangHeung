{
    "name": "Cost Centre",
    "version": "1.0",
    "category": "Accounting",
    "summary": "Module for managing Cost Centre in Journal Entries",
    "description": "This module allows users to manage Cost Centres associated with transactions.",
    "author": "CodeTrade India Pvt.Ltd.",
    "website": "https://www.codetrade.io",
    "depends": ["account", "base"],
    "data": [
        "security/ir.model.access.csv",
        "views/cost_centre_views.xml",
        "views/account_move_line.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}