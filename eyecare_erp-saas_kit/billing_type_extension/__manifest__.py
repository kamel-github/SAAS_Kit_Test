{
    "name": "SaaS-Master:Billing Type Extension",
    "version": "13.0.1.0",
    "depends": ['base', 'saas_product', 'saas_recurring'],
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    "summary": "SaaS Billing type extension module",
    'license': 'OPL-1',
    "description": """
    Performs some basic functions to setup billing types for saas functionalities
""",
    'website': 'http://www.pragtech.co.in',
    'init_xml': [],
    'data': [
        'views/saas_product_template_inherit.xml',
        'views/res_config_inherit.xml',
        'views/sale_order_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': True,
}
