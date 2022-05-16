{
    "name": "SaaS-Master:Tenant Module Upgrade",
    "version": "14.0.1",
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "depends": ["saas_base"],
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    'license': 'OPL-1',
    "summary": """ Module Upgrade in tenant database """,
    "description": """
    This module will enable user to upgrade modules in tenant database.
    This activity will be performed from saas master database itself.
""",
    'website': 'http://www.pragtech.co.in',
    'init_xml': [],
    'data': [
        'security/ir.model.access.csv',
        'wizards/tenant_db_upgrade_view.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': True,
}
