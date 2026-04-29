{
    'name': "POS Dynamic Discount",
    'summary': "Apply dynamic discounts based on product quantity in POS",
    'description': """
    This module extends the default POS discount functionality.
    
    Key Features:
    - Applies dynamic discounts based on selected product quantity.
    - Configurable discount rules for specific products.
    - Automatically adjusts pricing in the POS based on quantity thresholds.
    """,
    'author': "Codetrade",
    'website': "https://www.codetrade.io",
    'version': '0.2',
    'depends': ['point_of_sale','pos_loyalty'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_discount_config.xml',
        'views/product_template.xml',

    ],
     'assets': {'point_of_sale._assets_pos': [
         'pos_discount_config/static/src/js/discount_utils.js',
         'pos_discount_config/static/src/js/pos_discount_patch.js',
         'pos_discount_config/static/src/js/pos_order.js',
         'pos_discount_config/static/src/xml/pos_templates.xml',
     ],
    },
    'qweb': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
