{
    'name': 'POS Stock Validation',
    'version': '18.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Prevents POS orders for products with insufficient stock.',
    'description': """
This module enhances inventory integrity by blocking Point of Sale orders 
when a product's quantity on hand is not sufficient. It provides real-time 
feedback to the cashier to prevent overselling.
    """,
    'author': 'CodeTrade India Pvt.Ltd.',
    'website': 'https://www.codetrade.in',
    'depends': [
        'point_of_sale',
        'stock',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_stock_validation/static/src/js/validation_pop_up.js',
            'pos_stock_validation/static/src/js/PaymentScreen.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}