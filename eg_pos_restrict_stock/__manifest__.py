{
    "name": "POS Out of Stock Product Restriction",
    "version": "18.2",
    "category": "Point of Sale",
    "summary": "Enhance your Odoo POS system with the POS Restrict Stock module. This powerful tool automatically restricts out-of-stock products from being sold, preventing negative inventory. It ensures real-time synchronization with backend stock levels, improves stock visibility for cashiers, and streamlines retail operations with accuracy and efficiency. The POS Restrict Stock module for Odoo safeguards your sales process by automatically preventing the sale of products that have zero or negative stock in your Point of Sale system. This ensures that only available products can be sold, eliminating overselling and avoiding customer dissatisfaction caused by stock shortages. When activated, the module checks real-time inventory levels for every product in the POS interface. If a product is out of stock, it will be blocked from being added to the order line, ensuring complete alignment between your POS and backend stock data. This improves operational accuracy, minimizes refund scenarios, and helps businesses maintain trust and transparency with customers. POS restrict stock, POS block out-of-stock products, POS prevent overselling, POS zero stock control, POS negative stock restriction, POS real-time stock management, Restrict products with zero stock, Block unavailable products POS, POS inventory visibility, POS sales restriction module, Odoo POS restrict stock module, Odoo POS inventory restriction, Odoo prevent selling out-of-stock, Odoo POS negative stock prevention, Odoo real-time POS stock sync, Odoo POS stock management app, Odoo inventory control POS, Odoo POS oversell prevention, Odoo POS stock restriction addon, Odoo POS block zero quantity, Odoo POS restrict stock, Prevent negative inventory Odoo, Out of stock restriction POS, Real-time stock sync Odoo, Odoo POS inventory control, Stock visibility for cashiers,pos stock",
    "author": "INKERP",
    "website": "www.inkerp.com",
    "depends": [
        "point_of_sale"
    ],
    "data": [
        "views/pos_config_view.xml"
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "eg_pos_restrict_stock/static/src/xml/**/*",
            "eg_pos_restrict_stock/static/src/js/**/*"
        ]
    },
    "images": [
        "static/description/banner.png"
    ],
    "license": "OPL-1",
    "installable": True,
    "application": True,
    "auto_install": False,
    "price": "10.0",
    "currency": "EUR",
    "description": "Enhance your Odoo POS system by automatically restricting out of stock products from being sold. The POS Restrict Stock module helps prevent negative inventory, improves stock visibility for cashiers, and ensures real time synchronization with backend stock levels."
}