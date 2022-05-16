{
    'name': 'SaaS-Master: Product/pricing on Website',
    "version": "13.0.2.6",
    'depends': ['website', 'website_sale', 'mail', "saas_base","saas_sale"],
    'license': 'OPL-1',
    "summary": "To view the saas products",
    'website': 'http://www.pragtech.co.in',
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    "description": """
    Performs some saas product functions
""",
    'data': [
        'views/website_saas_menu.xml',
        'views/user_notification_template.xml',
        'views/saas_product_template.xml',
        'views/saas_tenant_details.xml',
        'views/saas_dbs_template.xml',
        'views/sale_order_view.xml',
        'views/res_config_view.xml',
        "file.sql",
    ],
    'application': 'True',
    'post_load': "unarchive_users",  # monkey patch
}
