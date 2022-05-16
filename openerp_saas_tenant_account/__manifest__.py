# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2010-2014 Elico Corp. All Rights Reserved.
#    Augustin Cisterne-Kaas <augustin.cisterne-kaas@elico-corp.com>
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
    'name': 'SaaS-Tenant:Saas Account',
    'version': '14.0.0',
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "summary": "Tenant Account",
    'category': 'Web',
    'license': 'OPL-1',
    'depends': ['openerp_saas_tenant', 'openerp_saas_tenant_extension'],
    'author': 'Pragmatic',
    'license': 'AGPL-3',
    'website': 'https://www.pragtech.co.inm',
    'description': """
        Tenant SaaS Account Details
    """,
    'images': [],
    'data': ['data/res_config_view.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
