{
    'name': 'Omni Print for POS: Direct Print Your Receipts',
    'summary': 'Directly print receipts and invoices with Omni Print for Point of Sale (PoS)',
    'description': """
        Seamlessly integrate Omni Print with Point of Sale (PoS) for direct receipt and invoice printing.
    """,
    'category': 'Point of Sale',
    'version': '1.0.1',
    'author': "Omni Byte",
    'website': "https://omni-byte.com/",
    'support': "support@omni-byte.com",
    'live_test_url': 'https://demo.omni-byte.com/',
    'images': ['static/description/main_screenshot.png'],
    'license': 'OPL-1',
    'price': 0,
    'currency': 'EUR',
    'depends': ['point_of_sale', 'omni_print'],
    'data': [
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'omni_print/static/src/network/*',
            'omni_print_pos/static/src/js/account_move_service.js',
            'omni_print_pos/static/src/js/printer.js',
            'omni_print_pos/static/src/js/pos_store.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}