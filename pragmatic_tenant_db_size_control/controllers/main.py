from odoo import http
import json
from odoo.http import request


class SaasProduct(http.Controller):
    @http.route(['/add_db_size'], type='http', auth="public", website=True, csrf=False)
    def add_db_size(self, **post):
        db_name = str(post['db']).split('|')
        if len(db_name) == 3:
            db_name = db_name[1]
        db_name = db_name.strip()
        gb_to_add = post['size']
        config_path = request.env['ir.config_parameter'].sudo()
        user_product = config_path.search(
            [('key', '=', 'db_size_usage_product')]).value
        product = request.env['product.product'].sudo().search([('id', '=', int(user_product))])
        order = request.website.sale_get_order(force_create=1)
        order.instance_name = db_name
        order._cart_update(product_id=product.id, add_qty=gb_to_add)
        data = 1
        return json.dumps(data)

    @http.route(['/add_filestore_size'], type='http', auth="public", website=True, csrf=False)
    def add_filestore_size(self, **post):
        db_name = str(post['db']).split('|')
        if len(db_name) == 3:
            db_name = db_name[1]
        db_name = db_name.strip()
        gb_to_add = post['size']
        config_path = request.env['ir.config_parameter'].sudo()
        user_product = config_path.search(
            [('key', '=', 'filestore_size_usage_product')]).value
        product = request.env['product.product'].sudo().search([('id', '=', int(user_product))])
        order = request.website.sale_get_order(force_create=1)
        order.instance_name = db_name
        order._cart_update(product_id=product.id, add_qty=gb_to_add)
        data = 1
        return json.dumps(data)
