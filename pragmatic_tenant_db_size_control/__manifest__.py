{
    'name': 'SaaS-Master:Tenant Database Size Control',
    'version': '13.0.10',
    'category': 'SaaS',
    'sequence': 1,
    'license': 'OPL-1',
    'description': """
    
    """,
    'author': 'Pragmatic TechSoft Pvt. Ltd.',
    'website': 'http://www.pragtech.co.in',
    'summary': '    ',
    'depends': ['saas_base', 'Bare_Tenant_Module_Installation','website_sale', 'saas_product'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_view.xml',
        'wizards/purchase_space_wizard.xml',
        'views/tenant_database_list.xml',
        'views/saas_tenant_details.xml',
        'views/cart.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'active': False,
}
