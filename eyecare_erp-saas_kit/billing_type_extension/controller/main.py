# import json
from odoo import http
from odoo.http import request
import json
import datetime
import xmlrpc
import logging
from odoo.exceptions import UserError

try:
    from odoo.addons.website_sale.controllers.main import WebsiteSale
except:
    from addons.website_sale.controllers.main import WebsiteSale


_logger = logging.getLogger(__name__)


class website_sale(WebsiteSale):

    @http.route(['/shop/order_confirm'], type='http', auth="public", website=True, sitemap=False)
    def payment_confirmation_order(self, **post):
        """ End of checkout process controller. Confirmation is basically seeing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        ICPSudo = request.env['ir.config_parameter'].sudo()
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)
        _logger.info('\n\nInside shop confirmation')
        # print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%_____________________________________________________________%", request.session)
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            if 'show_payment_acquire' in request.session:
                order.action_confirm1()
        else:
            raise UserError('no sale order')

        if 'show_payment_acquire' in request.session:
            del request.session['show_payment_acquire']
        if 'showing' in request.session:
            del request.session['showing']
        if 'select_payment_option' in request.session:
            del request.session['select_payment_option']
        #####################################################################
        # Calculate expiry date with selected term , only when the db is paid
        #####################################################################
        total_days = 0
        if order.invoice_ids.invoice_payment_state == 'paid':
            if order.invoice_term_id.name == 'Monthly':
                total_days = 30
            elif order.invoice_term_id.name == 'Yearly':
                total_days = 365
            if total_days:
                date = datetime.datetime.now().date()
                db = request.env['tenant.database.list'].sudo().search([('name', '=', order.instance_name)])
                db.exp_date = date + datetime.timedelta(days=total_days)

        # print('\n\nUpdating paid db users count after payment')

        ############################################
        # Updating paid db users count after payment
        ############################################
        config_path = request.env['ir.config_parameter'].sudo()
        user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        product = request.env['product.product'].sudo().search([('id', '=', int(user_product))])

        # print("\n\nProduct : ",user_product, product,order,order.invoice_ids,order.invoice_ids.line_ids)

        for lines in order.invoice_ids.line_ids:

            # print("\n\nlines : ",lines, order.invoice_ids.payment_state,product)

            if (lines.name == product.name) and (order.invoice_ids.invoice_payment_state == 'paid'):
                db = request.env['tenant.database.list'].sudo().search([('name', '=', order.instance_name)])
                db_name = order.instance_name
                uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                # print("\n\n\ndb : ", db, db_name, uid_dst)
                if db:

                    #Modified for billing type
                    if order.billing == 'normal':
                        db.no_of_users += order.order_line.product_uom_qty
                    else:
                        db.no_of_users = order.no_of_users

                    users = db.no_of_users
                    # print("\n\n\nUsers : ", order.order_line.product_uom_qty,db.no_of_users, users)
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                          [1,
                                           {
                                               'user_count': users
                                           }]
                                          )
        ############################################
        # Updating user database size after payment
        ############################################
        config_path = request.env['ir.config_parameter'].sudo()
        brand_website = config_path.search([('key', '=', 'brand_website')]).value
        brand_admin = config_path.search([('key', '=', 'admin_login')]).value
        brand_pwd = config_path.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))

        prod = 0
        if order.db_space == True:
            prod = 1
            db_size_product = config_path.search(
                [('key', '=', 'db_size_usage_product')]).value
        elif order.filestore_space == True:
            prod = 1
            db_size_product = config_path.search(
                [('key', '=', 'filestore_size_usage_product')]).value
        if prod == 1:
            db_product = request.env['product.product'].sudo().search([('id', '=', int(db_size_product))])
            for lines in order.invoice_ids.line_ids:
                if (db_product.name in lines.name) and (order.invoice_ids.invoice_payment_state == 'paid'):
                    db_name = order.instance_name
                    uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                    db = request.env['tenant.database.list'].sudo().search([('name', '=', db_name)])
                    if order.db_space == True:
                        tot_size = db.tenant_db_size + order.order_line.product_uom_qty
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [1,
                                               {
                                                   'tenant_db_size': tot_size,

                                               }]
                                              )

                        db.tenant_db_size = tot_size
                    elif order.filestore_space == True:
                        tot_size = db.tenant_filestore_size + order.order_line.product_uom_qty
                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'write',
                                              [1,
                                               {
                                                   'tenant_filestore_size': tot_size,

                                               }]
                                              )
                        db.tenant_filestore_size = tot_size

        return request.render("saas_product.confirmation1", {'order': order})

    @http.route(['/shop/getDefaultBillingType'], type='http', auth="public", website=True)
    def getdefaultbillingtype(self, **post):
        ICPSudo = request.env['ir.config_parameter'].sudo()
        billing = ICPSudo.search([('key', '=', 'billing')]).value
        vals = {'billing_type': billing}
        return json.dumps(vals)

    @http.route(['/shop/get_default_plan_users'], type='http', auth="public", website=True)
    def get_default_plan_users(self, **post):
        plan_users = 1
        if post.get('val') != 'normal':
            ICPSudo = request.env['ir.config_parameter'].sudo()
            plan_users = int(ICPSudo.search([('key', '=', 'plan_users')]).value or 1)

        return json.dumps({'plan_users': plan_users})

    @http.route(['/shop/get_user_product_price'], type='http', auth="public", website=True)
    def getuserProductSalePrice(self):
        ICPSudo = request.env['ir.config_parameter'].sudo()
        product_id = int(ICPSudo.search([('key', '=', 'user_product')]).value)
        ManageUserProduct = request.env['product.product'].search([('id', 'in', [product_id])], limit=1)
        # ManageUserProduct = request.env['product.product'].browse(product_id)
        # print(ManageUserProduct,"_______", product_id, "______________",ICPSudo.search([('key', '=', 'user_product')]).value)
        if ManageUserProduct:
            val = {'price': ManageUserProduct.lst_price}
        else:
            val = {'price': 0}
        return json.dumps(val)


    @http.route(['/shop/checkout2buy'], type='http', auth="public", website=True)
    def checkout2buy(self, **post):
        # print("post : ", post)
        ICPSudo = request.env['ir.config_parameter'].sudo()
        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)

        # if 'new_instance' in post and post['new_instance'] in [True, 'True', 'true'] and trial_days > 0:
        #     request.session['show_payment_acquire'] = False
        # else:
        #     request.session['show_payment_acquire'] = True

        order_test = request.website.sale_get_order()

        # sale_order_test = request.env['sale.order'].sudo().search([('id', '=', int(request.session['sale_order_id']))])
        sale_order = False
        pricelist_id = request.session.get('website_sale_current_pl') or request.env[
            'website'].get_current_pricelist().id
        partner = request.env.user.partner_id
        pricelist = request.env['product.pricelist'].browse(pricelist_id).sudo()

        so_data = request.env['website'].browse(1)._prepare_sale_order_values(partner, pricelist)

        so_data['instance_name'] = post.get('dbname')
        if 'term' in post:
            term = request.env['recurring.term'].sudo().search([('type', '=', post.get('term'))])
            so_data['invoice_term_id'] = term.id
            so_data['no_of_users'] = post.get('num')
            so_data['is_top_up'] = False
            so_data['new_instance'] = True
            so_data['tenant_language'] = post.get('language')
            so_data['billing'] = post.get('billing_type')

        # print("\n\nso_data : ", so_data)
        if 'sale_order_id' in request.session and request.session['sale_order_id']:
            sale_order = request.env['sale.order'].sudo().search([('id', '=', int(request.session['sale_order_id']))])
            sale_order.write(so_data)
        else:
            sale_order = request.env['sale.order'].sudo().create(so_data)
            request.session['sale_order_id'] = sale_order.id
            for order_line in sale_order.order_line:
                order_line.product_uom_qty = post.get('num')

        # Delete/Unlink exist product lines
        exist_ids = []
        for item in sale_order.order_line:
            exist_ids.append((3, item.id, False))
        sale_order.order_line = exist_ids

        if post.get('ids'):
            if 'product_ids' in request.session:
                request.session['product_ids'] = ''

            request.session['product_ids'] = post.get('ids')
            id_list = post.get('ids').split(',')
            id_list = list(map(int, id_list))
            for id in id_list:
                sale_order._cart_update(product_id=id, set_qty=1)

        exist = False
        state1 = request.env['sale.order'].sudo().search([('state', '=', 'sale'), ('id', '!=', sale_order.id)])
        for sale in request.env['sale.order'].sudo().search([('state', '=', 'sale'), ('id', '!=', sale_order.id)]):
            if sale.instance_name and sale.instance_name == post['dbname']:
                exist = True
                break
        return json.dumps({'exist': exist})


    @http.route(['/shop/payment'], type='http', auth="public", website=True)
    def payment(self, **post):
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        db_name = render_values['website_sale_order'].instance_name
        db = request.env['tenant.database.list'].sudo().search([('name', '=', db_name)])

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')
        # if 'sale_order_id' in request.session:
        #     request.session['sale_order_id']=''

        show = False
        if 'showing' in request.session:
            if request.session['showing'] == 2:
                render_values['showing'] = 2

        ICPSudo = request.env['ir.config_parameter'].sudo()
        if 'show_payment_acquire' in request.session and request.session['show_payment_acquire'] is True:
            show = True

        trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value or 0)
        render_values['show_payment_acquire'] = show
        render_values['free_days'] = trial_days

        # IF SHOW PAYMENTS DETAILS IS FALSE THE CARRY ONLY ONE ACQUIRER "WIRE TRANSFER"
        if show is False:
            acq = []
            for item in render_values['acquirers']:
                if 'Wire' in item.name or item.provider == 'transfer':
                    acq.append(item)
            render_values['acquirers'] = acq

            render_values['hide_acquirer_div'] = True
        else:
            render_values['hide_acquirer_div'] = False
        if show is True:
            acq = []
            for item in render_values['acquirers']:
                payment_mth = ICPSudo.search([('key', '=', 'payment_acquire')]).value
                acquire = request.env['payment.acquirer'].search([('id', '=', int(payment_mth))])
                if acquire.id == item.id:
                    pass
                else:
                    acq.append(item)

        render_values['acquirers'] = acq
        if not (db and db.free_trial == False):
            render_values['trial'] = 'True'
        config_path = request.env['ir.config_parameter'].sudo()
        sale_order_line = render_values['website_sale_order'].mapped("website_order_line")
        user_product = config_path.search(
            [('key', '=', 'user_product')]).value
        product = request.env['product.product'].sudo().search([('id', '=', int(user_product))])
        if render_values['website_sale_order'].billing == 'normal': # newly added
            for line in sale_order_line:
                if product == line.product_id:
                    render_values['add_more_user'] = 'True'

        return request.render("website_sale.payment", render_values)

    @http.route(['/shop/shop_cart_custom_update'], type='http', auth="public", website=True)
    def shop_cart_custom_update(self, **post):
        domain = ''
        try:
            domain = request.httprequest.environ['HTTP_X_FORWARDED_SERVER']
        except:
            domain = request.httprequest.environ['HTTP_HOST']

        path = request.httprequest.environ['PATH_INFO']
        http = request.httprequest.environ['HTTP_REFERER']
        if 'https' in http:
            http = 'https://'
        else:
            http = 'http://'

        if not request.session.uid:
            url = "/web/login?redirect=" + str(http) + "/" + str(domain) + "/" + str(path)
            url = url.replace('//', '/')
            return request.redirect(url)
        order = False

        order = request.website.sale_get_order()

        if order:
            for line in order.website_order_line:
                line.unlink()
        if 'product_ids' in request.session:
            ids = request.session['product_ids']

            ids = ids.split(",")
            pro_ids = []
            pro_ids = list(map(int, ids))
            for item in pro_ids:
                order = request.website.sale_get_order(force_create=1)._cart_update(
                    product_id=int(item),
                )
            # print("order :_____________", request.website.sale_get_order())
            ###########################################################################################
            order = request.website.sale_get_order()
            if order.billing == 'user_plan_price':
                config_path = request.env['ir.config_parameter'].sudo()
                config_user_product = config_path.search(
                    [('key', '=', 'user_product')]).value
                config_product = request.env['product.product'].sudo().search([('id', '=', int(config_user_product))])
                order._cart_update(product_id=config_product.id, set_qty=order.no_of_users)
                # print('Updated Cart')
            ###########################################################################################

        return request.redirect("/shop/address?partner_id=%s" % request.env.user.partner_id.id)

        so_line = request.env['sale.order.line'].sudo().browse(order.get('line_id'))
        render_values = {
            'website_sale_order': so_line.order_id,
            'partner_id': request.env.user.partner_id,
            'mode': ('edit', 'billing'),
            'checkout': so_line.order_id.partner_id,
            'country': None,  # country,
            'countries': request.env['res.country'].search([]),  # country.get_website_sale_countries(mode='edit'),
            "states": None,  # country.get_website_sale_states(mode='edit'),
            'error': {},
            'callback': None,
        }
        return request.render("website_sale.address", render_values)
