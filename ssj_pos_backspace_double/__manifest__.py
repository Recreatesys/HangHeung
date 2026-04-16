{
    "name": "POS Backspace Double Click",
    "version": "1.0",
    "category": "Point of Sale",
    "summary": "Auto double-fires the POS numpad backspace button on a single click",
    "author": "Recreatesys",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "ssj_pos_backspace_double/static/src/js/numpad_patch.js",
        ],
    },
    "installable": True,
    "auto_install": False,
}
