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
    "name": "SaaS-Master:Product View",
    "version": "13.1.15",
    'license': 'OPL-1',
    "depends": ["base", "sale_management", "base_setup", "payment_transfer", "web", "sale", "account_payment",
                "saas_base"],
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    "category": "SaaS",
    "summary": "SaaS sale product view",
    "description": """
    Performs some basic functions to setup saas functionalities
""",
    'website': 'http://www.pragtech.co.in',
    'init_xml': [],
    'data': [
        'data/recurring_term_data.xml',
        'views/product_view.xml',
        'views/sale_view.xml',
        'views/terms_view.xml',
        'views/sale_order_portal_view.xml',
        'views/invoice_order_portal_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [],
    'installable': True,
}
