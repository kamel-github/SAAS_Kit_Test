{
    "name": "SaaS-Master:Database Filter Module",
    "version": "14.0.0.4",
    "depends": ['saas_base'],
    'license': 'OPL-1',
    "summary": "To filter SaaS Database",
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "Tools",
    "description": """
    To filter database based on URL entered by the user
""",
    'website': 'http://www.pragtech.co.in',
    'depends': ['base'],
    'update_xml': [],
    'data': [
        'views/view.xml',
        # 'views/assets.xml'
    ],
    'auto_install': True,
    'installable': True,
    'application': False,
    'bootstrap': True,
}
