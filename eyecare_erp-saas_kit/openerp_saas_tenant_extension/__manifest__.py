{
    'name': 'SaaS-Tenant:',
    'version': '14.0.0.3',
    'category': 'SaaS',
    'description': """Openerp SAAS Tenant Restriction Module """,
    "summary": "Tenant restriction",
    'website': 'http://www.pragtech.co.in',
    'author': 'Pragmatic TechSoft Pvt. Ltd.',
    'license': 'OPL-1',
    'depends': ['openerp_saas_tenant' ],
    'data': [
        'security/saas_service_security.xml',
        'security/ir.model.access.csv',
        'views/template.xml',
        # 'views/users_view.xml',
        # 'vies/account_bank_view.xml',
    ],
    'qweb': [
        # 'static/src/xml/base.xml',
    ],

    'installable': True,
    'active': True,
}
