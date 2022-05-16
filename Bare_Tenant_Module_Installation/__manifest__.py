# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    "name": "SaaS-Master:Bare Tenant Module Installation",
    "version": "14.0.9",
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "depends": ["db_filter","saas_base"],
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    'license': 'OPL-1',
    "summary": """ Module Installation in tenant database """,
    "description": """
    This module will enable user to install / uninstall modules in tenant database.
    This activity will be performed from saas master database itself.
""",
    'website': 'http://www.pragtech.co.in',
    'init_xml': [],
    'data': [
        'views/bare_tenant_module.xml',
        'views/tenant_modules.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
    'active': True,
}
