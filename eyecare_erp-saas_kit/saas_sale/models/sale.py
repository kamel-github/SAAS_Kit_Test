# -*- coding: utf-8 -*-
from odoo import fields
import datetime
import odoo
from odoo.api import Environment
from odoo import _
from functools import partial
from odoo.tools.misc import formatLang
from odoo.tools import config
import logging
import time
from odoo.service import db
from odoo.tools.float_utils import float_round as round
from odoo import api, models
import xmlrpc
from odoo.exceptions import UserError, Warning
import traceback
from odoo.http import request
from odoo.addons.website_sale.models.website import Website
import psycopg2
from contextlib import closing

_logger = logging.getLogger(__name__)

ADMINUSER_ID = 2


def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
    """ Return the current sales order after mofications specified by params.
    :param bool force_create: Create sales order if not already existing
    :param str code: Code to force a pricelist (promo code)
                     If empty, it's a special case to reset the pricelist with the first available else the default.
    :param bool update_pricelist: Force to recompute all the lines from sales order to adapt the price with the current pricelist.
    :param int force_pricelist: pricelist_id - if set,  we change the pricelist with this one
    :returns: browse record for the current sales order
    """
    if not self.env.user:
        return False

    self.ensure_one()
    partner = self.env.user.partner_id
    sale_order_id = request.session.get('sale_order_id')
    if not sale_order_id and not self.env.user._is_public():
        last_order = partner.last_website_so_id
        if last_order:
            available_pricelists = self.get_pricelist_available()
            # Do not reload the cart of this user last visit if the cart uses a pricelist no longer available.
            sale_order_id = last_order.pricelist_id in available_pricelists and last_order.id

    # Test validity of the sale_order_id
    sale_order = self.env['sale.order'].sudo().browse(sale_order_id).exists() if sale_order_id else None

    if not (sale_order or force_create or code):
        if request.session.get('sale_order_id'):
            request.session['sale_order_id'] = None
        return self.env['sale.order']

    if self.env['product.pricelist'].browse(force_pricelist).exists():
        pricelist_id = force_pricelist
        request.session['website_sale_current_pl'] = pricelist_id
        update_pricelist = True
    else:
        pricelist_id = request.session.get('website_sale_current_pl') or self.get_current_pricelist().id

    if not self._context.get('pricelist'):
        self = self.with_context(pricelist=pricelist_id)

    # cart creation was requested (either explicitly or to configure a promo code)
    if not sale_order:
        # TODO cache partner_id session
        pricelist = self.env['product.pricelist'].browse(pricelist_id).sudo()
        so_data = self._prepare_sale_order_values(partner, pricelist)
        sale_order = self.env['sale.order'].with_context(with_company=request.website.company_id.id).sudo().create(
            so_data)

        # set fiscal position
        if request.website.partner_id.id != partner.id:
            sale_order.onchange_partner_shipping_id()
        else:  # For public user, fiscal position based on geolocation
            country_code = request.session['geoip'].get('country_code')
            if country_code:
                country_id = request.env['res.country'].search([('code', '=', country_code)], limit=1).id
                fp_id = request.env['account.fiscal.position'].sudo().with_context(
                    force_company=request.website.company_id.id)._get_fpos_by_region(country_id)
                sale_order.fiscal_position_id = fp_id
            else:
                # if no geolocation, use the public user fp
                sale_order.onchange_partner_shipping_id()

        request.session['sale_order_id'] = sale_order.id

    # case when user emptied the cart
    if not request.session.get('sale_order_id'):
        request.session['sale_order_id'] = sale_order.id

    # check for change of pricelist with a coupon
    pricelist_id = pricelist_id or partner.property_product_pricelist.id

    # check for change of partner_id ie after signup
    if sale_order.partner_id.id != partner.id and request.website.partner_id.id != partner.id:
        flag_pricelist = False
        if pricelist_id != sale_order.pricelist_id.id:
            flag_pricelist = True
        fiscal_position = sale_order.fiscal_position_id.id

        # change the partner, and trigger the onchange
        sale_order.write({'partner_id': partner.id})
        sale_order.onchange_partner_id()
        sale_order.write({'partner_invoice_id': partner.id})
        sale_order.onchange_partner_shipping_id()  # fiscal position
        sale_order['payment_term_id'] = self.sale_get_payment_term(partner)

        # check the pricelist : update it if the pricelist is not the 'forced' one
        values = {}
        if sale_order.pricelist_id:
            if sale_order.pricelist_id.id != pricelist_id:
                values['pricelist_id'] = pricelist_id
                update_pricelist = True

        # if fiscal position, update the order lines taxes
        if sale_order.fiscal_position_id:
            sale_order._compute_tax_id()

        # if values, then make the SO update
        if values:
            sale_order.write(values)

        # check if the fiscal position has changed with the partner_id update
        recent_fiscal_position = sale_order.fiscal_position_id.id
        if flag_pricelist or recent_fiscal_position != fiscal_position:
            update_pricelist = True

    if code and code != sale_order.pricelist_id.code:
        code_pricelist = self.env['product.pricelist'].sudo().search([('code', '=', code)], limit=1)
        if code_pricelist:
            pricelist_id = code_pricelist.id
            update_pricelist = True
    elif code is not None and sale_order.pricelist_id.code and code != sale_order.pricelist_id.code:
        # code is not None when user removes code and click on "Apply"
        pricelist_id = partner.property_product_pricelist.id
        update_pricelist = True

    # update the pricelist
    if update_pricelist:
        request.session['website_sale_current_pl'] = pricelist_id
        values = {'pricelist_id': pricelist_id}
        # print("\n\nvalues : ", values)
        sale_order.write(values)
        for line in sale_order.order_line:
            # print('\n\n Line order : ', line.product_uom_qty, sale_order.no_of_users)
            if line.exists():
                sale_order._cart_update(product_id=line.product_id.id, line_id=line.id, add_qty=0)

    return sale_order


Website.sale_get_order = sale_get_order


class RPCProxyOne(object):
    def __init__(self, server, ressource):
        """Class to store one RPC proxy server."""
        self.server = server
        local_url = 'http://%s:%d/xmlrpc/common' % (server.server_url,
                                                    server.server_port)
        rpc = xmlrpc.client.ServerProxy(local_url)
        self.uid = rpc.login(server.server_db, server.login, server.password)
        local_url = 'http://%s:%d/xmlrpc/object' % (server.server_url,
                                                    server.server_port)
        self.rpc = xmlrpc.client.ServerProxy(local_url)
        self.ressource = ressource

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.rpc.execute(self.server.server_db,
                                                        self.uid,
                                                        self.server.password,
                                                        self.ressource, name,
                                                        *args)


class RPCProxy(object):
    """Class to store RPC proxy server."""

    def __init__(self, server):
        self.server = server

    def get(self, ressource):
        return RPCProxyOne(self.server, ressource)


class Users(models.Model):
    _inherit = 'res.users'

    tenant_user = fields.Boolean('Tenant User dummy field (no use in master db)')


class sale_order(models.Model):
    _inherit = 'sale.order'

    billing = fields.Selection([('normal', 'Per Module/Per Month/Per User'),
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type", default="normal")

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                if line.month > 0:
                    amount_tax += line.price_tax * line.month
                else:
                    amount_tax += line.price_tax

            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def _amount_all_temp(self, field_name, arg):
        """Method overridden as it is without calling 'super' to calculate tax according to no. of months in subscription.
        """
        cur_obj = self.env['res.currency']
        res = {}
        for order in self:
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }

            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(line)
                # multiply by no. of months in a subscription
                val *= line.month
            res[order.id]['amount_tax'] = cur_obj.round(cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

    def check_so_to_confirm(self):
        ## Cron/Scheduler method to check SO's for auto confirm if " Auto process free trial SO's " is checked
        ## This method will search for all SO's having state 'sent' i.e. paid from customer and are not top-up

        sent_sale_orders = self.search(
            [('state', 'in', ['sent', 'draft']), ('is_top_up', '!=', True), ('instance_name', '!=', False)])
        ## instance_name != False means sale order is a SaaS sale order bcoz normal sale order dosn't have instance name.
        for sent_sale_order in sent_sale_orders:
            #                 self.env['sale.order'].action_confirm(  [sent_sale_order] )
            sent_sale_order.action_confirm()

        return True

    def update_cart_price(self, post):
        # =======================================================================
        # Method to update product price according to date on which it is purchase
        # If purchase order is at middle of the month don't take cost for all month
        # =======================================================================
        if self.is_top_up:
            ICPSudo = self.env['ir.config_parameter'].sudo()

            for line in self.order_line:
                product = line.product_id
                original_price = 0
                if product.is_saas:
                    price_unit = product.list_price
                    original_price = price_unit
                    instance_name = self.instance_name
                    db_ids = self.env['tenant.database.list'].search([('name', '=', instance_name)], limit=1)
                    exp_date = False
                    if db_ids:
                        exp_date = db_ids.exp_date

                    if exp_date:
                        ##for different subscription terms take respective No .of months
                        months_to_add = 0
                        term_type = db_ids.invoice_term_id.type
                        if term_type == 'from_first_date': months_to_add = 1
                        if term_type == 'quarter': months_to_add = 3
                        if term_type == 'half_year': months_to_add = 6
                        if term_type == 'year': months_to_add = 12

                        ## Find start date from exp_date and no of months, to calculate total days in subscription term
                        start_date = str(datetime.datetime.strptime(str(exp_date), '%Y-%m-%d') - datetime.timedelta(
                            months_to_add * 365 / 12).isoformat())[:10]
                        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")

                        exp_date = datetime.datetime.strptime(exp_date, "%Y-%m-%d")
                        total_days = exp_date - start_date
                        total_days = total_days.total_seconds() / 60 / 60 / 24

                        ##If it is trial period take only trial days configured in configurations.
                        if ICPSudo.search([('key', '=', 'free_trial')]).value:
                            total_days = ICPSudo.search([('key', '=', 'free_trial_days')]).value or 30

                        ##Find remaining days.
                        today_date = datetime.datetime.today()
                        days_to_pay = exp_date - today_date
                        days_to_pay = days_to_pay.total_seconds() / 60 / 60 / 24
                        days_to_pay = days_to_pay + 1  # It was given one day less thats why added 1 day.

                        price_unit_per_day = price_unit / int(total_days)
                        price_unit = price_unit_per_day * int(days_to_pay)
                        if price_unit < 0: price_unit = price_unit * (-1)

                        # print('asdfsdfsfsfsdf++++++++++++++++++++++++++++++++++++++++++++++++')
                        line.write({'price_unit': price_unit})
                        self._cr.commit()

                        ##If it is trial period take price as it is.
                        if self.env['tenant.database.list'].browse(db_ids[0]).free_trial:
                            line.write({'price_unit': original_price})

                        self._cr.commit()
        return True

    def write(self, vals=None):
        ##Overridden for auto confirm of Top-Up Order
        if 'no_of_users' in vals:
            print(222, vals)
        res = False

        if 'confirmation_date' in vals and 'state' in vals and vals['state'] == 'sale':
            self._cr.execute("update sale_order set state='%s' where id =%s" % (vals['state'], self.id))
            self._cr.execute(
                "update sale_order set confirmation_date='%s' where id =%s" % (vals['confirmation_date'], self.id))
            del vals['confirmation_date']
            res = True
            # res = super(sale_order, self).write(vals)
        else:
            try:
                res = super(sale_order, self).write(vals)
            except Exception as e:
                print(e)

        return res

    def copy(self, default=None):
        default = default or {}
        if 'name' in default and default['name'] in ['New, new']:
            default['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
        if 'name' not in default:
            default['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')

        return super(sale_order, self).copy(default)

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        if 'name' in vals and vals['name'] in ['New, new']:
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
        if 'name' not in vals:
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
        if 'uid' in self._context:
            vals['user_uid'] = self._context['uid']
        return models.Model.create(self, vals)

    # passing the no_of_users to compute all methode
    def _amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            users = self.no_of_users
            print("usersssssssssss444444444444", users)
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = \
                    line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id,
                                            partner=order.partner_shipping_id, users=users)['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]

    @api.model
    def _is_saas_order(self):
        # =======================================================================
        # Method returns order type, whether it is SaaS type or not
        # =======================================================================
        for sale in self:
            is_saas = False
            if sale.order_line:
                for line in sale.order_line:
                    if line.product_id.is_saas:
                        is_saas = True
                        break
            sale.saas_order = is_saas

    @api.model
    def _get_user_dbs(self):
        # =======================================================================
        # Method to get list of all DB's associated to specific user
        # =======================================================================
        res = {}
        for sale in self:
            db_ids = self.env['tenant.database.list'].search([('user_id', '=', self._context.get('uid'))])
            res[sale.id] = db_ids
        return res

    user_uid = fields.Many2one('res.users', "User")
    instance_name = fields.Char('Database Name', size=64)
    instance_name_list = fields.Many2one('tenant.database.list', compute='_get_user_dbs', string='saaS order')
    saas_order = fields.Boolean(compute='_is_saas_order', string='SaaS Order')
    no_of_users = fields.Integer('No. of Users', default=1)
    # for payment methode(pay now/trial)
    free_trial = fields.Boolean('Free Trial')
    is_top_up = fields.Boolean('Is top-up?', readonly=True)
    new_instance = fields.Boolean('New Instance', readonly=True)
    existed_product = fields.Char('product Name', size=500)
    pwd = fields.Text('Random Generated Password')
    saas_domain = fields.Char('SaaS Domain', size=50, compute="get_tenant_url")
    temp_vals = fields.Char('saaS domain', size=200)
    invoice_term_id = fields.Many2one('recurring.term', 'Invoicing Term')
    company_name = fields.Char('Customer Company Name', size=128)
    customer_name = fields.Char('Customer Name', size=128)
    customer_email = fields.Char('Customer Email Address', size=128)
    lang_code = fields.Char('Language Code', size=64, default='en_US')

    def get_tenant_url(self):
        so_line = self.env['sale.order'].search([])
        ICPSudo = self.env['ir.config_parameter'].sudo()
        domain = ICPSudo.search([('key', '=', 'domain_name')]).value
        if not domain.startswith('.'):
            domain = '.' + domain
        self.saas_domain = "%s%s" % (self.instance_name, domain)

    def random_password(self):
        # =======================================================================
        # Returns random string containing alphanumeric Characters
        # =======================================================================
        import random
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        pw_length = 8
        mypw = ""
        for i in range(pw_length):
            next_index = random.randrange(len(alphabet))
            mypw = mypw + alphabet[next_index]
        return mypw

    def set_logo(self):
        db_name = str(self.instance_name).lower().replace(" ", "_")
        registry = odoo.registry(db_name)

        ## Set Service provider Company Logo to tenant database initially

        with closing(registry.cursor()) as cr:
            env = Environment(cr, ADMINUSER_ID, {})
            admin_company_ids = self.env['res.company'].search([], limit=1)
            if admin_company_ids:
                tenant_company_ids = env['res.company'].search([])
                for tenant_company in tenant_company_ids:
                    #                     comp_obj=env['res.company'].browse(tenant_company)
                    tenant_company.write({'logo': admin_company_ids.logo})
            cr.commit()

    def _make_invoice(self, order, lines=None):
        invoice_line_obj = self.env['account.move.line']
        if lines and order.saas_order:
            # ===================================================================
            # If product is SaaS type and free trial period give 100% discount
            # ===================================================================
            db_name = order.instance_name
            db_ids = self.env['tenant.database.list'].search([('name', '=', db_name)])
            free_trial = False
            if db_ids:
                free_trial = db_ids.free_trial
            for line in invoice_line_obj.browse(lines):
                if line.product_id.is_saas and free_trial:
                    line.write({'discount': 100})
        _logger.info(_('Inside make invoice function  : {} {}'.format(order, lines)))
        res = super(sale_order, self)._make_invoice(order, lines)
        return res

    def action_install_module(self, db_name, module_list):
        ## XMLRPC CONNECTION
        ICPSudo = self.env['ir.config_parameter'].sudo()
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        domain_website = ICPSudo.search([('key', '=', 'domain_name')]).value
        # print("\n\n_____________values to connect ", db_name, brand_admin, brand_pwd)
        uid = 0
        uid_dst = 0
        try:
            uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
            if not uid_dst:
                uid_dst = common.authenticate(db_name, 'admin', 'admin', {})
                brand_pwd = 'admin'
        except Exception as e:
            print('\n\nError ___________ : ', e)

        ## XMLRPC
        max_group_id = max(dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search', [[]]))
        module_ids_to_install = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.module.module', 'search',
                                                      [[('name', 'in', module_list)]])
        try:
            num = 0
            for module_id in module_ids_to_install:
                num = num + 1
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.module.module', 'button_immediate_install',
                                      [module_id])
        except Exception as e:
            print(e)
        try:
            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work', [2],
                                  {'max_group_id': max_group_id or 9000})
        except Exception as e:
            if 'has no attribute' in str(e):
                pass
            else:
                raise UserError(e)

    def _auto_open_invoice(self, move_id):
        self.env['account.move'].signal_workflow([move_id], 'invoice_open')
        _logger.info('SaaS-post Trail Period invoice is open automatically for invoice %s' % (str(move_id)))
        return True

    def _auto_paid_invoice(self, move_id=None):
        ## create account voucher record to create payment
        voucher_obj = self.env['account.move']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        voucher_line_obj = self.env['account.move.line']
        inv = invoice_obj.browse(move_id)
        '''
            their may be multiple cash type journals has been found, 
            we are consider 1st one to do the payment.    
        '''
        journal_ids = journal_obj.search([('type', '=', 'cash')])
        journal = journal_obj.browse(journal_ids[0])
        if not journal_ids:
            raise UserError(
                _('Warning', 'Did not found any cash type Journal.. Please configure it from Journal Master'))
        partner_id = self.env['res.partner']._find_accounting_partner(inv.partner_id)
        vals = {
            'partner_id': partner_id.id,
            'period_id': inv.period_id.id,
            'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
            'reference': inv.name,
            'close_after_process': True,
            'invoice_type': inv.type,
            'move_id': inv.id,
            'type': inv.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
            'journal_id': journal_ids[0],
            'account_id': journal.default_credit_account_id.id,
            'date': time.strftime('%Y-%m-%d'),
            'currency_id': inv.currency_id,
            'name': inv.name,
            'number': inv.number,
        }

        voucher_id = voucher_obj.create(vals)
        for move in inv.move_id.line_id:
            line = voucher_line_obj.create({
                'voucher_id': voucher_id,
                'amount': inv.amount_total,
                'amount_original': inv.amount_total,
                'account_id': inv.partner_id.property_account_receivable.id,
                'move_line_id': move.id,
                'type': 'cr',
            })
            break
        conText = self._context
        if conText is None:
            conText = {
                'move_id': inv.id
            }
        voucher_obj.button_proforma_voucher([voucher_id])
        return True

    def create_discounted_invoice(self):
        invoice_line_obj = self.env['account.move.line']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        today = time.strftime('%Y-%m-%d')
        res = journal_obj.search([('type', '=', 'sale')], limit=1)
        journal_id = res and res[0] or False

        account_id = self.sale_order_ref.partner_id.property_account_receivable_id.id
        invoice_vals = {
            'name': self.name,
            'invoice_origin': self.name,
            'comment': 'SaaS Recurring Invoice',
            'no_of_users': self.no_of_users,
            'invoice_term_id': self.invoice_term_id.id,
            'date_invoice': today,
            'address_invoice_id': self.partner_invoice_id.id,
            'user_id': self._uid,
            'partner_id': self.partner_id.id,
            'account_id': account_id,
            'journal_id': journal_id.id,
            'sale_order_ids': [(4, self.id)],
            'instance_name': str(self.instance_name).encode('utf-8'),
        }
        move_id = invoice_obj.create(invoice_vals)

        for line in self.order_line:
            print("last price :",line.product_id.lst_price)
            invoice_line_vals = {
                'name': line.product_id.name,
                'invoice_origin': 'SaaS-Kit-' + self.name,
                'move_id': move_id.id,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                'account_id': line.product_id.categ_id.property_account_income_categ_id.id,
                'price_unit': line.product_id.lst_price,
                'discount': 100,
                'quantity': 1,
                'price_subtotal': line.price_subtotal,
                'account_analytic_id': False,
            }
            # print('asdfsafsfsdf',invoice_line_vals)
            if line.product_id.taxes_id.id:
                invoice_line_vals['invoice_line_tax_ids'] = [
                    [6, False, [line.product_id.taxes_id.id]]]  # [(6, 0, [line.product_id.taxes_id.id])],

            invoice_line_obj.create(invoice_line_vals)

            ##make payment paid
            total = move_id.residual
            partner_type = False
            if move_id.partner_id:
                if total < 0:
                    partner_type = 'supplier'
                else:
                    partner_type = 'customer'
            payment_methods = (
                                      total > 0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
            currency = self.journal_id.currency_id or self.company_id.currency_id
            payment = self.env['account.payment'].create({
                'payment_method_id': payment_methods and payment_methods[0].id or False,
                'payment_type': total > 0 and 'inbound' or 'outbound',
                'partner_id': self.partner_id and self.partner_id.id or False,
                'partner_type': partner_type,
                'journal_id': self.statement_id.journal_id.id,
                'payment_date': self.date,
                'state': 'reconciled',
                'currency_id': currency.id,
                'amount': abs(total),
                'communication': self._get_communication(payment_methods[0] if payment_methods else False),
                'name': self.statement_id.name,
            })
            payment.action_validate_invoice_payment()

    def create_database_if_not_exist(self, db_name):
        is_created = False
        try:
            exist = False
            ##Check if database name exists in og_database table. Return True if present

            _logger.info('SaaS-Tenant %(db)s creation started' % {'db': db_name})
            self._cr.execute(
                "SELECT u.usename  FROM pg_database d  JOIN pg_user u ON (d.datdba = u.usesysid) WHERE d.datname = '%s'; " % self._cr.dbname)
            current_db_owner = str(self._cr.fetchone()[0])
            self._cr.execute(
                "SELECT u.usename  FROM pg_database d  JOIN pg_user u ON (d.datdba = u.usesysid) WHERE d.datname = 'bare_tenant_13'; ")
            bare_db_owner = str(self._cr.fetchone()[0])
            if current_db_owner != bare_db_owner:
                self._cr.execute('grant "%s" to "%s"' % (bare_db_owner, current_db_owner))
                self._cr.commit()

            self._cr.commit()

            registry = odoo.registry(db_name)

            if current_db_owner != bare_db_owner:
                # if owner not same change owner to current_db_owner
                tables = []
                with closing(registry.cursor()) as tenant_cr:
                    tenant_cr.execute("select tablename from pg_tables where schemaname = 'public'")
                    result = tenant_cr.fetchall()
                    for item in result:
                        if item:
                            tables.append(str(item[0]))
                    tenant_cr.execute(
                        "select sequence_name from information_schema.sequences where sequence_schema = 'public'")
                    result = tenant_cr.fetchall()
                    for item in result:
                        if item:
                            tables.append(str(item[0]))

                    tenant_cr.execute("select table_name from information_schema.views where table_schema = 'public'")
                    result = tenant_cr.fetchall()
                    for item in result:
                        if item:
                            tables.append(str(item[0]))
                    for table in tables:
                        tenant_cr.execute("alter table %s owner to %s" % (table, current_db_owner))
                    tenant_cr.commit()
                    self._cr.execute("revoke %s from %s" % (bare_db_owner, current_db_owner))

        except Exception as e:
            import traceback
            if 'already exists' in str(e):
                raise UserError(_('Database already exist.'))
            else:
                raise UserError(_('Error\n %s') % str(e))
        return is_created

    def send_db_creation_mail(self, db_name):

        ##Send DB creation mail
        email_template_obj = self.env['mail.template']
        mail_template_id = self.env['ir.model.data'].get_object_reference(
            'saas_sale', 'email_template_database_creation')
        email_template_obj.browse(mail_template_id[1]).send_mail(self.id, force_send=True)
        _logger.info('mail Sent')
        _logger.info('Tenant %(db_name)s is created successfully' % {'db_name': db_name})

    def post_installation_work(self):
        order = self
        tenant_database_list_obj = self.env['tenant.database.list']
        ICPSudo = self.env['ir.config_parameter'].sudo()

        db_size = ICPSudo.search([('key', '=', 'tenant_db_size')]).value
        filestore_size = ICPSudo.search([('key', '=', 'tenant_filestore_size')]).value
        brand_name = ICPSudo.search([('key', '=', 'brand_name')]).value
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        db_name = str(order.instance_name).lower().replace(" ", "_")
        order.instance_name = db_name
        admin_login = str(ICPSudo.search([('key', '=', 'admin_login')]).value) or 'admin'
        admin_pwd = str(ICPSudo.search([('key', '=', 'admin_pwd')]).value) or 'admin'
        _logger.info('\n\nDatabase Name %s', db_name)
        _logger.info('\n\nDatabase size %s', db_size)
        _logger.info('\n\nDatabase filestore_size %s', filestore_size)
        _logger.info('\n\nDatabase brand_website %s', brand_website)
        _logger.info('\n\nDatabase Name %s', db_name)
        order_date = datetime.datetime.strptime(str(datetime.date.today()), '%Y-%m-%d')

        if order.invoice_term_id.type == 'year':
            free_trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value) or 365
        else:
            free_trial_days = int(ICPSudo.search([('key', '=', 'free_trial_days')]).value) or 30
        exp_date = str(order_date + datetime.timedelta(days=free_trial_days))[:10]
        new_user_id = False
        psuedo_user_pwd = self.random_password()
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        _logger.info('\n\nDest Model %s', dest_model)
        _logger.info('\n\ncommon %s', common)
        _logger.info('\n\nDB NAME %s', db_name)
        _logger.info('\n\nbrand_pwd %s', brand_pwd)
        # _logger.info('\n\nsudo_pwd %s', psuedo_user_pwd)
        uid_dst = common.authenticate(db_name, admin_login, brand_pwd, {})
        _logger.info('\n\nuid_dst %s', uid_dst)
        if not uid_dst:
            uid_dst = common.authenticate(db_name, 'admin', 'admin', {})
            brand_pwd = 'admin'

        if uid_dst:
            ##CREATE COPY OF ADMIN USER AND CREATE SERVICE RECORD

            #             tenant_env = Environment(tenant_cr, ADMINUSER_ID, {})
            #             admin_user = tenant_env['res.users'].browse(ADMINUSER_ID)
            #             new_user_id = admin_user.copy({
            #                                        'login': order.customer_email or order.partner_id.email,
            #                                        'name': order.customer_name or order.partner_id.name,
            #                                        'password': psuedo_user_pwd,
            #                                        })

            ############################################################################################
            # Install Selected language
            #############################################################################################
            if self.tenant_language:
                _logger.info('\n\nInstalling Language {} in tenant {}'.format(self.tenant_language.name,
                                                                              self.tenant_language.code))

                res_lang_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.lang', 'search',
                                                     [[['code', 'ilike', self.tenant_language.code],
                                                       ['active', 'in', [True, False]]]])

                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.lang', 'write',
                                      [res_lang_ids,
                                       {
                                           'active': True,
                                       }]
                                      )

                _logger.info(
                    '\n\nInstalling Language {} found in tenant with id {}'.format(self.tenant_language.name,
                                                                                   res_lang_ids))
                if res_lang_ids:
                    lang_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.lang',
                                                     'install_language', [res_lang_ids])
                    if lang_ids:
                        _logger.info('\n\nInstalling Language {} in tenant {} Successful'.format(
                            self.tenant_language.name, db_name))
                    else:
                        _logger.warning('\n\nInstalling Language {} not found in tenant {}'.format(
                            self.tenant_language.name, db_name))
                else:
                    _logger.warning(
                        '\n\nLanguage {} not found in tenant {}'.format(self.tenant_language.name, db_name))
            #############################################################################################

            new_user_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'copy',
                                                [2,
                                                 {
                                                     'login': order.customer_email or order.partner_id.email,
                                                     'name': order.customer_name or order.partner_id.name,
                                                     'password': psuedo_user_pwd,
                                                 }]
                                                )

            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                  [new_user_id,
                                   {
                                       'active': 't',
                                   }]
                                  )
            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                  [2,
                                   {
                                       'password': brand_pwd or 'admin',
                                       'login': admin_login or 'admin',
                                   }]
                                  )

            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'saas.service', 'create',
                                  [{
                                      'use_user_count': 1,
                                      'user_count': order.no_of_users,
                                      'name': db_name,
                                      'expiry_date': exp_date,
                                      'tenant_db_size': db_size,
                                      'tenant_filestore_size': filestore_size,
                                  }]
                                  )

            #             admin_user.password = admin_pwd or 'admin'
            #             admin_user.login = admin_login or 'admin'

            #             tenant_cr.execute("""INSERT INTO saas_service
            #                                 (use_user_count,user_count,name,expiry_date)
            #                                 VALUES (1,%s,'%s','%s')""" % (order.no_of_users, db_name, exp_date))

            group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                              [[('name', '=', 'My Service Access')]])
            for group_id in group_ids:
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                      [new_user_id,
                                       {
                                           'tenant_user': True,
                                           'in_group_' + str(group_id): True if group_id else '',
                                       }]
                                      )

            #             group_id = tenant_env['res.groups'].sudo().search([('name','=', 'My Service Access')], limit=1)
            #             new_user_id.write({
            #                               'tenant_user': True,
            #                               'in_group_'+str(group_id.id):True if group_id else '',
            #                             })
            # CHANGE_ODOO_LABELS_TO_BRAND_NAME
            tenant_msg_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'mail.message', 'search',
                                                  [[('subject', '=', 'Welcome to Odoo!')]])
            for msg in tenant_msg_id:
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'mail.message', 'write',
                                      [msg,
                                       {
                                           'subject': 'Welcome to %s!' % brand_name,
                                       }]
                                      )

            #             tenant_msg_id  = tenant_env['mail.message'].search( [('subject', '=', 'Welcome to Odoo!')])
            #             for msg in tenant_msg_id:
            #                 msg.subject = 'Welcome to %s!' % brand_name

            trans_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.translation', 'search',
                                              [[('value', 'ilike', 'odoo')]])
            for item in trans_ids:
                # item2 = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.translation', 'search', [item])

                translation = False
                try:
                    translation = str((item.value.encode("utf-8")))
                except Exception as e:
                    print(e)
                if translation:
                    value1 = translation.replace("Odoo's", str(brand_name) + "'s")
                    value2 = value1.replace("Odoo", str(brand_name))
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.translation', 'write',
                                          [item,
                                           {
                                               'value': value2,
                                           }]
                                          )

        #             trans_ids = tenant_env['ir.translation'].search( [('value', 'ilike', 'odoo')])
        #             for item in trans_ids:
        #                 translation = False
        #                 try:
        #                     translation = str((item.value.encode("utf-8")))
        #                 except:
        #                     print (1)
        #                 if translation:
        #                     value1 = translation.replace("Odoo's", str(brand_name)+"'s")
        #                     value2 = value1.replace("Odoo", str(brand_name))
        #                     item.value = value2

        ##Create Tenant Database List Record
        stage_ids = self.env['tenant.database.stage'].search([('is_active', '=', True)])

        tenant_database_list_vals = {
            'name': db_name,
            'exp_date': exp_date,
            'free_trial': order.free_trial,
            'sale_order_ref': order.id,
            'no_of_users': order.no_of_users,
            'invoice_term_id': order.invoice_term_id.id,
            'stage_id': stage_ids.id if stage_ids else False,
            'user_pwd': psuedo_user_pwd,
            'billing': order.billing,
            'super_user_login': admin_login,
            'super_user_pwd': brand_pwd,
            'user_login': order.customer_email or order.partner_id.email
        }
        tenant_database_id = tenant_database_list_obj.create(tenant_database_list_vals)

        # WRITE TENANT USER PWD IN SO TO SEND IT IN A MAIL TO USER
        self.pwd = psuedo_user_pwd
        self.send_db_creation_mail(db_name)
        # ------------End-------------------------

        ## XMLRPC WORK
        #         tenant_env = Environment(tenant_cr, ADMINUSER_ID, {})
        #         alias_id = tenant_env['ir.config_parameter'].search([('key', '=', 'mail.catchall.domain')])
        #
        #         if alias_id:
        #             alias_id.value = brand_website or ''
        #         else:
        #             alias_domain = db_name + "."+str(brand_website.replace('www.',''))
        #             tenant_env['ir.config_parameter'].create( {'key':'mail.catchall.domain', 'value':alias_domain})

        ##To check Enable password reset from login page
        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.config.settings', 'create',
                              [{'auth_signup_reset_password': True, }])

        #         login_check_id = tenant_env['res.config.settings'].create({'auth_signup_reset_password':True})
        #         tenant_cr.commit()

        ## SET TENANT SUPER USER GROUP TO SUPERADMIN USER
        ## COPY ALL ACCESS RIGHTS AND SET THEM A PSUEDO ADMIN GROUP
        group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                          [[
                                              '|', '|',
                                              ['name', '=', 'My Service Access'],
                                              ['name', '=', 'Technical Features'],
                                              ['name', '=', 'Tenant Super User'],
                                          ]]
                                          )
        for group in group_ids:
            try:
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work2', [2],
                                      {'group_id': group})
            except Exception as e:
                print(e)

        #         group_id = tenant_env['res.groups'].sudo().search([('name', 'in', ['Tenant Super User', 'My Service Access', 'Technical Features'])])
        #         for group in group_id:
        #             try:
        #                 tenant_cr.execute("select gid from res_groups_users_rel where gid=%s and uid=%s"%(group.id, 2))
        #                 data = tenant_cr.fetchall()
        #                 if not data:
        #                     tenant_cr.execute("insert into res_groups_users_rel(gid, uid) values(%s, %s)" % (group.id, 2))
        #             except:
        #                 print ("already fulfilled.")

        ## SET GOUPS_ID TO FALSE IN 'IR_UI_MENU'
        menu_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.ui.menu', 'search',
                                        [[
                                            ('complete_name', '=', 'Settings/Translations/Languages'),
                                            ('name', '=', 'Languages')
                                        ]])
        if menu_id:
            group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                              [[
                                                  ('full_name', '=', 'Settings/Translations/Languages'),
                                                  ('name', '=', 'Languages')
                                              ]])

            groups_ids_menu = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users',
                                                    'perform_many2many_table_work_browse1', [2],
                                                    {'menu_id': menu_id})

            groups_ids = set(groups_ids_menu) - set(group_ids)

            if groups_ids:
                groups_ids = list(groups_ids)
            else:
                groups_ids = []

            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.ui.menu', 'write',
                                  [menu_id,
                                   {
                                       'groups_id': [(6, False, groups_ids)]
                                   }]
                                  )

        #         menu_id = tenant_env['ir.ui.menu'].search(  [('complete_name', '=', 'Settings/Translations/Languages'), ('name', '=', 'Languages')])
        #         if menu_id:
        #             group_id = tenant_env['res.groups'].search([('name', '=', 'Technical Features'), ('category_id.name', '=', 'Usability')])
        #             groups_ids = [rec.id for rec in menu_id.groups_id]
        #             groups_ids = set(groups_ids) - set(group_id.ids)
        #             if groups_ids:
        #                 groups_ids = list(groups_ids)
        #             else:
        #                 groups_ids = []
        #
        #             tenant_env['ir.ui.menu'].browse(menu_id.id).write({'groups_id':[(6, False, groups_ids)]})

        #             ## SET ALL LANGUAGE FIELDS AS PER GIVEN FORMAT
        #             lang_ids = tenant_env['res.lang'].search([])
        #             for lang in lang_ids:
        #                 lang.write( {'date_format':'%d/%m/%Y', 'time_format': '%H:%M', 'decimal_point':'.', 'thousands_sep':','})

        ## GIVE ALL AVAILABLE RIGHTS
        if new_user_id:
            technical_settings_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.module.category', 'search',
                                                          [[
                                                              '|',
                                                              ['name', '=', 'technische instellingen'],
                                                              ['name', '=', 'Technical Settings'],
                                                          ]])

            group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                              [[
                                                  '|', '|',
                                                  ['category_id', '=', 'technical_settings_id'],
                                                  ['name', '=', 'Employee'],
                                                  ['name', '=', 'Psuedo Admin']
                                              ]])

            for group_id in group_ids:
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work3', [2],
                                      {'group_id': group_id, 'new_user_id': new_user_id})

        #         if new_user_id:
        #             res_groups_obj = tenant_env['res.groups']
        #             technical_settings_id = tenant_env['ir.module.category'].search([('name', 'in', ['Technical Settings', 'technische instellingen'])]).ids
        #             group_ids = res_groups_obj.search( ['|', '|', ('category_id', 'in', technical_settings_id),
        #                                                 ('name', '=', 'Employee'),
        #                                                 ('name', '=', 'Psuedo Admin')])
        #             for group_id in group_ids:
        #
        #                 tenant_cr.execute("select * from res_groups_users_rel where gid=%s and uid=%s" % (group_id.id, new_user_id.id))
        #                 result = tenant_cr.fetchall()
        #                 if not result:
        #                     tenant_cr.execute("insert into res_groups_users_rel(gid, uid) values(%s, %s)" % (group_id.id, new_user_id.id))
        #                 else:
        #                     print (1)

        # commented due to time issue ajaykrishna
        ## COPY ALL ACCESS RIGHTS AND SET THEM A PSUEDO ADMIN GROUP
        # group_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
        #                                  [[
        #                                      ('name', '=', 'My Service Access')
        #                                  ]])
        # if group_id:
        #     access_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'search',
        #                                        [[]])
        #     total = len(access_ids)
        #     count = 0
        #     for access in access_ids:
        #         count = count + 1
        #         try:
        #             new_access_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'copy',
        #                                                   [access,
        #                                                    {
        #
        #                                                    }]
        #                                                   )
        #             dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'write',
        #                                   [new_access_id,
        #                                    {
        #                                        'group_id': group_id,
        #                                        'perm_unlink': True,
        #                                        'perm_write': True,
        #                                        'perm_create': True,
        #                                        'perm_read': True,
        #                                    }]
        #                                   )
        #         except Exception as e:
        #             print(e)

        #         group_id = res_groups_obj.sudo().search([('name', '=', 'My Service Access')])
        #         if group_id:
        #             access_ids = tenant_env['ir.model.access'].search([])
        #             total = len(access_ids.ids)
        #             count = 0
        #             for access in access_ids:
        #                 count = count + 1
        #                 try:
        #                     new_access_id = access.copy()
        #                     tenant_cr.execute("update ir_model_access set group_id = %s, perm_unlink = true, perm_write = true, perm_create = true, perm_read = true where id=%s"%(group.id, new_access_id.id))
        #
        #                 except:
        #                     print (123)

        ## REMOVE TECHNICAL FEATURES RIGHT FROM USERS OTHER THAN ADMIN
        # technical_settings_group_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
        #                                             [[
        #                                             ('name', '=', 'Technical Features')
        #                                             ]])
        # for id in technical_settings_group_id:
        #     dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work4', [2],
        #                                             {'group_id': id})

        #         res_groups_obj = tenant_env['res.groups']
        #         technical_settings_group_id = res_groups_obj.search([('name', '=', 'Technical Features')])
        #         if technical_settings_group_id:
        #             tenant_cr.execute("delete from res_groups_users_rel where gid=%d and uid!=%d" % (technical_settings_group_id[0].id, ADMINUSER_ID))
        #             tenant_cr.commit()

        ## REMOVE TENANT SUPER USER RIGHT FROM ALL TENANT USERS
        tenant_settings_group_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                         [[
                                                             ('name', '=', 'Tenant Super User')
                                                         ]])
        for id in tenant_settings_group_id:
            tenant_user_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'search',
                                                    [[('id', '>', 2)]])
            for user in tenant_user_ids:
                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'perform_many2many_table_work5', [2],
                                      {'group_id': id, 'user_id': user})

        #         res_groups_obj = tenant_env['res.groups']
        #         tenant_super_user_group_id = res_groups_obj.search([('name', '=', 'Tenant Super User')])
        #         tenant_user_ids = tenant_env['res.users'].sudo().search([('id', '>', 2)])
        #         for group in tenant_super_user_group_id:
        #             for user in tenant_user_ids:
        #                 tenant_cr.execute("delete from res_groups_users_rel where gid=%d and uid=%d" % (group.id, user.id))

        #             ## REMOVE TECHNICAL FEATURES RIGHT FROM USERS OTHER THAN ADMIN
        #             res_groups_obj = tenant_env['res.groups']
        #             technical_settings_group_id = res_groups_obj.search([('name', '=', 'Access Rights')])
        #             if technical_settings_group_id:
        #                 tenant_cr.execute("delete from res_groups_users_rel where gid=%d and uid!=%d" % (technical_settings_group_id[0].id, ADMINUSER_ID))

        #             ## To change currency position to before of value
        #             currency_ids = tenant_env['res.currency'].search([])
        #             for curr in currency_ids:
        #                 curr.write( {'position':'before'})

        ## HIDING ALL ODOO WORDS from ACTIONS
        action_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.actions.act_window', 'search',
                                           [[]])

        for action in action_ids:
            help = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users',
                                         'perform_many2many_table_work_browse2', [2],
                                         {'act_id': action})

            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.actions.act_window', 'write',
                                  [action,
                                   {
                                       'help': str(help or '').replace('Odoo', brand_name)
                                   }]
                                  )

    def action_confirm1(self):
        # =======================================================================
        # call super of sale order to generate sales order
        # =======================================================================
        ICPSudo = self.env['ir.config_parameter'].sudo()
        buy_product_id = int(ICPSudo.search([('key', '=', 'buy_product')]).value or False)
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        total_days = ICPSudo.search([('key', '=', 'free_trial_days')]).value or 30

        if not brand_admin:
            raise UserError('Please Configure SaaS Settings')

        partner = self.partner_id
        country = partner.country_id
        accounting_module = ''
        name_module = False

        # if self.state not in ['sent', 'draft']:
        #     return True
        if not self.saas_order:
            return super(sale_order, self).action_confirm()

        if not self._context: conText = {}
        module_list = []
        if self.saas_order and not self.instance_name:
            raise UserError('Please provide Instance Name!')

        self = self.sudo()
        if self.order_line:
            for line in self.order_line:
                if line.product_id.is_saas and line.product_id != buy_product_id:
                    if line.product_id.product_tmpl_id.module_list:
                        module_list += [m.name for m in line.product_id.product_tmpl_id.module_list]
        # if 'website' in module_list:

        db_name = self.instance_name
        _logger.info('Module to be install on tenant database %(db)s started ' % {'db': str(module_list)})
        # =======================================================================
        # create tenant database and record and install modules
        # =======================================================================
        # tenant_db_obj = self.env['tenant.database.list'].sudo().search([('name', '=', self.instance_name)])
        # if tenant_db_obj:
        #     raise UserError("Database already available")
        if self.saas_order:
            ## create new user with name tenant name
            ## Auto install "web_adblock" to tenant DB
            # module_list.append('web_adblock')
            self._cr.execute("SELECT datname FROM pg_database WHERE datistemplate = false;")

            db_names = self._cr.fetchall()
            exist = False
            for item in db_names:
                if item:
                    if db_name == str(item[0]):
                        exist = True
                        if not self.is_top_up:
                            _logger.info('\n\nDatabase is already exist : {}\n\n'.format(db_name))
                            raise UserError(_('Database "%s" is already exists...!' % db_name))
                        else:
                            break

            if not exist:
                config = odoo.tools.config
                _logger.info('Bare Database NAme Form Config : {} {}'.format(config, config['bare_db']))
                db.exp_duplicate_database(config['bare_db'], db_name)
                # ===================================================================
                # Change admin password of tenant database as per configured in SaaS Configuration.
                # ===================================================================
                registry = odoo.registry(db_name)
                tenant_db = odoo.sql_db.db_connect(db_name)
                tenant_cr = tenant_db.cursor()
                ICPSudo = self.env['ir.config_parameter'].sudo()
                brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
                admin_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
                with registry.cursor() as cr:
                    env = Environment(cr, ADMINUSER_ID, {})
                    super_user_login = None
                    env['res.users'].browse(2).write({'login': brand_admin})
                    tenant_cr.commit()
                    if admin_pwd:
                        env['res.users'].browse(2).write({'password': admin_pwd})
                        tenant_cr.commit()
                    else:
                        env['res.users'].browse(2).write({'password': 'admin'})
                        tenant_cr.commit()
                    tenant_cr.close()
            self.action_install_module(db_name, ['sales_team', 'openerp_saas_tenant'])
            self.action_install_module(db_name, module_list)
            self.action_install_module(db_name, ['sale_group', 'db_filter'])
            self.action_install_module(db_name, ['openerp_saas_tenant_extension', 'web_saas'])
            self.action_install_module(db_name, ['openerp_saas_tenant_account', 'contacts'])
            if not exist:
                _logger.info('\n\nAdded record in Saasmaster_v13 to access tenant Info\n\n')
                self.post_installation_work()

        res = super(sale_order, self).action_confirm()

        for line in self.order_line:
            for list_module in line.product_id.product_tmpl_id.module_list:
                name_module = list_module.name
        if name_module == 'account':
            module = self.env['ir.module.module'].sudo().search([('name', '=', 'l10n_%s' % country.code.lower())])
            if module:
                accounting_module = module.name

        if accounting_module:
            self.action_install_module(db_name, [accounting_module])

        for sale_order_object in self:
            sale_recurring_order_obj = self.env['sale.recurring.orders.agreement'].sudo()
            recurring_order_rel_obj = self.env['sale.recurring.orders.agreement.order']

            dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
            common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
            uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})

            # =======================================================================
            # 'from_existed_agreement' : Agreement will create first time only if the order is related to Saas products
            # =======================================================================
            ## TODO:" check agreement is already created for this order
            agreement = recurring_order_rel_obj.sudo().search([('order_id', '=', sale_order_object.id)])

            if not agreement:

                if sale_order_object.instance_name:
                    recurring_order_name = 'SaaS-' + sale_order_object.name

                    date_time = time.strftime("%d") + '/' + time.strftime("%b") + '/' + time.strftime(
                        "%Y") + ' ' + time.strftime("%X")
                    agreement_id = None

                    if not sale_order_object.is_top_up:
                        start_date = sale_order_object.date_order
                        end_date = start_date + datetime.timedelta(days=int(total_days))

                        agreement_vals = {
                            'state': 'first',
                            'name': recurring_order_name,
                            'partner_id': sale_order_object.partner_id.id,
                            'start_date': start_date,
                            'company_id': sale_order_object.company_id.id,
                            'end_date': end_date,
                            'billing': sale_order_object.billing,
                            'version_no': '1.1',
                            'log_history': date_time + ' :- Agreement is created',
                            'invoice_term_id': sale_order_object.invoice_term_id.id,
                            'instance_name': str(sale_order_object.instance_name).encode('utf-8'),
                            'active': True,
                        }
                        agreement_id = sale_recurring_order_obj.sudo().create(agreement_vals)
                    else:
                        ## XMLRPC
                        last_group_id = max(
                            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search', [[]]))
                        last_access_control_id = max(
                            dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'search', [[]]))

                        for x in module_list:
                            self.action_install_module(self.instance_name, [x])

                        group_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                          [[['id', '>', last_group_id]]])
                        user_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'search', [[]])
                        for user in user_ids:
                            for group in group_ids:
                                dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.users', 'write',
                                                      [user,
                                                       {
                                                           'in_group_' + str(group): True if group else ''
                                                       }]
                                                      )
                                # user.write({'in_group_' + str(group.id):True if group else '',})

                        group_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'res.groups', 'search',
                                                         [[['name', '=', 'Tenant Super User']]])
                        if group_id:
                            access_ids = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'search',
                                                               [[['id', '>', last_access_control_id]]])
                            for access_id in access_ids:
                                try:
                                    new_access_id = dest_model.execute_kw(db_name, uid_dst, brand_pwd,
                                                                          'ir.model.access', 'copy',
                                                                          [access_id,
                                                                           {

                                                                           }]
                                                                          )
                                    for group in group_id:
                                        dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'ir.model.access', 'write',
                                                              [new_access_id,
                                                               {
                                                                   'group_id': group,
                                                                   'perm_unlink': 't',
                                                                   'perm_write': 't',
                                                                   'perm_create': 't',
                                                                   'perm_read': 't',
                                                               }]
                                                              )
                                except Exception as e:
                                    print(e)

                        ## If sale_order is top-up order don't create new agreement.
                        ## Instead of this use existing agreement and update it with new sale_order and product line
                        agreement_id = self.env['sale.recurring.orders.agreement'].sudo().search(
                            [('partner_id', '=', sale_order_object.partner_id.id),
                             ('active', '=', True),
                             ('instance_name', '=', sale_order_object.instance_name)])

                    # ===========================================================
                    # Check if product is bundle product or simple product
                    # If product is bundle product, line 'sale_recurring_order_line_obj'
                    # will contain all bundle products and main product
                    # ===========================================================
                    for line in sale_order_object.order_line:
                        # ===========================================================
                        # Add main product also
                        # ===========================================================

                        values_2 = {
                            'agreement_id': agreement_id[0].id,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'quantity': line.product_uom_qty,
                            'price': line.price_unit,
                            'ordering_interval': '1',
                            'ordering_unit': 'years',
                            'createdate': time.strftime('%Y-%m-%d %H:%M:%S'),
                        }

                        self.env['sale.recurring.orders.agreement.line'].sudo().create(values_2)

                    ## write sale order reference in agreement
                    values_3 = {
                        'agreement_id': agreement_id[0].id,
                        'order_id': sale_order_object.id,
                    }
                    self.env['sale.recurring.orders.agreement.order'].sudo().create(values_3)
                    # self.env.cr.execute("INSERT INTO sale_recurring_orders_agreement_order(agreement_id, order_id) VALUES (%s, %s)" % (agreement_id.id,sale_order_object.id))

        return res

    def create_first_invoice(self):
        invoice_line_obj = self.env['account.move.line']
        invoice_obj = self.env['account.move']
        journal_obj = self.env['account.journal']
        today = time.strftime('%Y-%m-%d')
        move_id = None
        res = journal_obj.search([('type', '=', 'sale')], limit=1)
        journal_id = res and res[0] or False
        account_id = self.partner_id.property_account_receivable_id.id
        invoice_vals = {
            'name': self.name,
            'invoice_origin': self.name,
            'comment': 'First Invoice',
            'date_invoice': today,
            'address_invoice_id': self.partner_invoice_id.id,
            'user_id': self._uid,
            'partner_id': self.partner_id.id,
            'no_of_users': self.no_of_users,
            'invoice_term_id': self.invoice_term_id.id,
            'account_id': account_id,
            'journal_id': journal_id.id,
            'sale_order_ids': [(4, self.id)],
            'instance_name': str(self.instance_name).encode('utf-8'),
        }
        move_id = invoice_obj.create(invoice_vals)

        ## make invoice line from the agreement product line
        for line in self.order_line:
            qty = line.product_uom_qty
            print("last price 222222222:",line.product_id.lst_price)
            invoice_line_vals = {
                'name': line.product_id.name,
                'invoice_origin': self.name,
                'move_id': move_id.id,
                'uom_id': line.product_id.uom_id.id,
                'product_id': line.product_id.id,
                'account_id': line.product_id.categ_id.property_account_income_categ_id.id,
                'price_unit': line.product_id.lst_price,
                'discount': line.discount,
                'quantity': qty,
                'price_subtotal': line.price_subtotal,
                'account_analytic_id': False,
            }
            if line.product_id.taxes_id.id:
                invoice_line_vals['invoice_line_tax_ids'] = [
                    [6, False, [line.product_id.taxes_id.id]]]  # [(6, 0, [line.product_id.taxes_id.id])],

            invoice_line_obj.create(invoice_line_vals)

        # recompute taxes(Update taxes)
        return move_id

    def _prepare_invoice(self):
        invoice_vals = super(sale_order, self)._prepare_invoice()

        invoice_vals['instance_name'] = self.instance_name
        invoice_vals['no_of_users'] = self.no_of_users
        invoice_vals['invoice_term_id'] = self.invoice_term_id.id
        #         invoice_vals.update(self._inv_get())
        return invoice_vals


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('qty_invoiced', 'qty_delivered', 'product_uom_qty', 'order_id.state')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.order_id.state in ['sale', 'done']:
                if line.product_id.invoice_policy == 'order':
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_delivered - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    @api.depends('state', 'price_reduce', 'product_id', 'untaxed_amount_invoiced', 'qty_delivered')
    def _compute_untaxed_amount_to_invoice(self):

        """ Total of remaining amount to invoice on the sale order line (taxes excl.) as
                total_sol - amount already invoiced
            where Total_sol depends on the invoice policy of the product.

            Note: Draft invoice are ignored on purpose, the 'to invoice' amount should
            come only from the SO lines.
        """
        for line in self:
            amount_to_invoice = 0.0
            if line.state in ['sale', 'done']:
                # Note: do not use price_subtotal field as it returns zero when the ordered quantity is
                # zero. It causes problem for expense line (e.i.: ordered qty = 0, deli qty = 4,
                # price_unit = 20 ; subtotal is zero), but when you can invoice the line, you see an
                # amount and not zero. Since we compute untaxed amount, we can use directly the price
                # reduce (to include discount) without using `compute_all()` method on taxes.
                price_subtotal = 0.0
                if line.product_id.invoice_policy == 'delivery':

                    price_subtotal = line.price_reduce * line.qty_delivered
                else:
                    price_subtotal = line.price_reduce * line.product_uom_qty

                amount_to_invoice = price_subtotal - line.untaxed_amount_invoiced
            line.untaxed_amount_to_invoice = amount_to_invoice * line.month

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            users = line.order_id.no_of_users or 1
            print("usersssssssssss3333333333333333333", users)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id,
                                            line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id,
                                            users=users)
            tax = (taxes['total_included'] - taxes['total_excluded'])

            if line.month:
                price_subtotal = taxes['total_excluded'] * line.month
                if line.month > 0 and line.order_id.no_of_users > 0:
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': price_subtotal + tax,
                        'price_subtotal': price_subtotal,
                    })
                    # print('\n\n line.price_unit :', line.price_unit, line.price_subtotal, line.price_total)



                else:
                    for line in self:
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        users = line.order_id.no_of_users
                        print("usersssssssssss22222222222", users)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id,
                                                        line.product_uom_qty,
                                                        product=line.product_id,
                                                        partner=line.order_id.partner_shipping_id,
                                                        users=users)
                        tax = (taxes['total_included'] - taxes['total_excluded'])
                        price_subtotal = taxes['total_excluded']
                        line.update({
                            'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'price_total': price_subtotal + tax,
                            'price_subtotal': price_subtotal,
                        })

    def _get_invoice_term_months(self):
        res = {}
        if self.order_id.saas_order:
            for sol in self:
                res[sol.id] = 1
                instance_name = sol.order_id.instance_name
                if instance_name:
                    # ===============================================================
                    # On "Confirm" click
                    # For new and top up both orders Charge for all months in subscription use this code
                    # ======================= Start ========================================
                    type = sol.order_id.invoice_term_id.type
                    if type == 'from_first_date': sol.month = 1
                    if type == 'quarter': sol.month = 3
                    if type == 'half_year': sol.month = 6
                    if type == 'year': sol.month = 12
                    if type is False or None: sol.month = 1
                else:
                    self.month = 1
                # =================== End ================================================
        else:
            self.month = 1
        return res

    @api.model
    # @api.returns('self', lambda value:value.id)
    def create(self, vals):
        product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
        if 'product_uos_qty' in vals:
            vals['product_uom_qty'] = vals['product_uos_qty']
        if 'price_unit' in vals:
            vals.update({'name': product_id.name})
        return models.Model.create(self, vals)

    def write(self, vals):
        # print("\n\nOrder Lines vals :", vals)
        if 'price_unit' in vals:
            print(111111111, vals)
        return models.Model.write(self, vals)

    # 'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
    month = fields.Integer(compute='_get_invoice_term_months', string='Invoice Term', default=1)

    # for invoice line
    def _prepare_invoice_line(self, **optional_values):
        """
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        :param optional_values: any parameter that should be added to the returned invoice line
        """
        ##############################################################   Old Code0
        # self.ensure_one()
        # res = {
        #     'display_type': self.display_type,
        #     'sequence': self.sequence,
        #     'name': self.name,
        #     'product_id': self.product_id.id,
        #     'product_uom_id': self.product_uom.id,
        #     'quantity': self.qty_to_invoice,
        #     'discount': self.discount,
        #     'price_unit': self.price_unit,
        #     'tax_ids': [(6, 0, self.tax_id.ids)],
        #     'analytic_account_id': self.order_id.analytic_account_id.id,
        #     'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
        #     'sale_line_ids': [(4, self.id)],
        # }

        # if optional_values:
        #     res.update(optional_values)
        # if self.display_type:
        #     res['account_id'] = False
        ##############################################################3333
        
        res = super(sale_order_line, self)._prepare_invoice_line()
        months = 1
        if not self.order_id.website_id:
            if self.order_id.invoice_term_id:
                if self.order_id.invoice_term_id.name == 'Yearly':
                    months = 12

            # for line in self.invoice_line_ids:
            if self.order_id.no_of_users > 0 and self.order_id.billing == 'normal':
                res.update({'price_unit' : (res.get('price_unit') / (self.order_id.no_of_users * months))})
                # print("\n price unit      :", res.get('price_unit'))
            else:
                product_id = self.env['product.product'].search([('id', '=', res.get('product_id'))])
                res.update({'price_unit': product_id.lst_price * months})
                res.update({'price_subtotal': res.get('price_unit') * res.get('quantity') })
        
        return res


class account_invoice(models.Model):
    _inherit = 'account.move'
    """ inherited to add some new fields"""

    billing = fields.Selection([('normal', 'Per Module/Per Month/Per User'),
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type", default="normal")

    # updating invoice values while creating
    # @api.model_create_multi
    # def create(self, vals_list):
    #     vals_list = self._move_autocomplete_invoice_lines_create(vals_list)
    #     print("\n\nAccount move create vals : ", vals_list)
    #     rslt = super(account_invoice, self).create(vals_list)
    
    #     ###########for yearly and monthly basis
    #     months = 1
    #     if rslt.invoice_term_id:
    #         if rslt.invoice_term_id.name == 'Yearly':
    #             months = 12
    #     for line in rslt.invoice_line_ids:
    #         if line.move_id.no_of_users > 0 and line.move_id.billing == 'normal':
    #             line.price_unit = (line.price_unit / (line.move_id.no_of_users * months))
    #             print("\n price unit      :", line.price_unit)
    #         else:
    #             line.write({'price_unit' : line.product_id.lst_price * months})
    #             line.write({'price_subtotal' : line.price_unit * line.quantity})
    #             print("price subtotal         :", line.price_subtotal, "\n price unit      :", line.price_unit,'\n Amount Tax:   :',rslt.amount_tax)
    
    #     print("Created Invoice: ", rslt)
    #     return rslt


    def write(self, vals):
        print('\n\naccount move write : ',vals)
        return super(account_invoice, self).write(vals)

    def _get_expiry(self):

        for item in self:

            db = self.env['tenant.database.list'].search([('name', '=', item.instance_name)], limit=1)
            if db:
                item.expiry_date = db.exp_date

    instance_name = fields.Char('Database Name', size=64)
    # user_count = fields.Integer("User Count")
    no_of_users = fields.Integer('No. of Users', default=1)
    invoice_term_id = fields.Many2one('recurring.term', 'Invoicing Term')
    invoice_type = fields.Selection([('rent', 'Rent Invoice'), ('user', 'User Purchase Invoice')],
                                    string="Invoice Type")
    expiry_date = fields.Date(compute='_get_expiry', string="Expiry Date")


class account_voucher(models.Model):
    _inherit = 'account.move'
    """ Inherited to renew database expiration on paying invoice"""

    def button_proforma_voucher(self, conText=None):
        res = super(account_voucher, self).button_proforma_voucher(conText)
        invoice_obj = self.env['account.move']
        tenant_db_list_obj = self.env['tenant.database.list']
        config = odoo.tools.config
        db_name = str(invoice_obj.browse(conText['move_id']).instance_name)
        invoice = invoice_obj.browse(conText['move_id'])

        agreement = self.env['sale.recurring.orders.agreement'].sudo().search([('instance_name', '=', db_name)])
        if not agreement:
            return res

        #         if invoice.instance_name and invoice.amount_total != 0.00:
        #              """Code for Trial Expiry"""
        ## if the invoice amt is 0 then direct return
        tenant_db_id = tenant_db_list_obj.search([('name', '=', db_name)])
        tenant_db = tenant_db_list_obj.browse(tenant_db_id)
        if type(tenant_db) is list:
            tenant_db = tenant_db[0]
        #             old_exp_date = tenant_db[0].exp_date
        #         old_exp_date = tenant_db[0].next_invoice_create_date

        ##for different subscription terms take respective No .of months
        months_to_add = 0
        term_type = tenant_db.invoice_term_id.type
        if term_type == 'from_first_date': months_to_add = 1
        if term_type == 'quarter': months_to_add = 3
        if term_type == 'half_year': months_to_add = 6
        if term_type == 'year': months_to_add = 12

        #             new_exp_date = str(mx.DateTime.strptime(str(old_exp_date),'%Y-%m-%d') + RelativeDateTime(months=months_to_add))[:10]

        ##If all pending invoices paid, allow to active db
        allow_to_active_db = True

        sale_id = self.env['sale.order'].search([('instance_name', '=', db_name)], limit=1)
        if sale_id:
            so_name = sale_id.name
            draft_invoices_ids_so = invoice_obj.search([('invoice_origin', '=', so_name), ('state', '!=', 'posted')])
            if draft_invoices_ids_so:
                allow_to_active_db = False

        if allow_to_active_db:
            # if tenant_db[0].expired:
            #                 new_exp_date = str(mx.DateTime.strptime(str(old_exp_date),'%Y-%m-%d') + RelativeDateTime(months=months_to_add))[:10]
            new_exp_date = False  ##tenant_db[0].next_invoice_create_date

            ## In case if tenant DB doesn't have 'next_invoice_create_date' date, 'new_exp_date' will set to blank
            ## To avoid this calculate tenant's 'new_exp_date' from it's subscription term.
            if not new_exp_date:
                ##If subscription period is monthly and 3 invoices are missed.
                ##In this case we added 3 months to get 'new_exp_date', i.e. 'new_exp_date' should be greater than Today's date
                new_exp_date = tenant_db.exp_date
                while True:
                    new_exp_date = str(datetime.datetime.strptime(str(new_exp_date), '%Y-%m-%d') + datetime.timedelta(
                        months=months_to_add))[:10]
                    new_exp_date = new_exp_date.split('-')
                    y = new_exp_date[0]
                    m = new_exp_date[1]
                    d = new_exp_date[2]
                    new_exp_date = datetime.datetime.strptime(d + '' + m + '' + y, '%d%m%Y').date()
                    today = datetime.datetime.now().date()
                    if new_exp_date > today:
                        break

            self._cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': db_name, 'role': config['db_user']})
            active_stage_id = self.env['tenant.database.stage'].search([('is_active', '=', True)], limit=1)
            tenant_db_list_obj.write([tenant_db.id], {'free_trial': False,
                                                      'expired': False,
                                                      'exp_date': new_exp_date,
                                                      'stage_id': active_stage_id.id if active_stage_id else False
                                                      })

            db = self
            pool = self
            with closing(db.cursor()) as slave_cr:
                saas_service_obj_ids = pool.get('saas.service').sudo().search(slave_cr, ADMINUSER_ID, [])
                pool.get('saas.service').sudo().write(slave_cr, ADMINUSER_ID, saas_service_obj_ids,
                                                      {'expiry_date': new_exp_date})
                slave_cr.commit()

        email_template_obj = self.env['mail.template']
        mail_template_id = self.env['ir.model.data'].get_object_reference(
            'openerp_saas_instance', 'email_template_renew_subscription')

        #         email_template_obj.send_mail(  mail_template_id[1], tenant_db.id, force_send=True,conText=conText)
        mail_template_id.send_mail(tenant_db.id, force_send=True)
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    """Inherited For calculate the subtotal price in invoice line with number of users"""

    def create(self, vals):
        # print('\n\nCreate Account Move line vals :', vals)
        res = super(AccountMoveLine, self).create(vals)
        # print('\n\n Created Move line :', res)
        return res

    def write(self, vals):
        # print('\n\nWrite Account Move line vals :', vals)
        res = super(AccountMoveLine, self).write(vals)
        # print('\n\n Updated Move line :', res)
        return res

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes,
                                            move_type):
        # print('\n\nCalculated price for invoice :',price_unit, quantity, discount, currency, product, partner, taxes,
        #                                    self,move_type)
        res = {}
        # Compute 'price_subtotal'.
        no_of_users = self.move_id.no_of_users
        payment_term = self.move_id.invoice_term_id
        months = 1
        if payment_term:
            if payment_term.name == 'Monthly':
                months = 1
            if payment_term.name == 'Yearly':
                months = 12
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit * no_of_users * months
        # tots = quantity * line_discount_price_unit * no_of_users * months
        # Compute 'price_total'.
        if taxes:
            no_of_users = no_of_users * months
            print("usersssssssssss11111111111111",no_of_users)
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner,
                                                                                      is_refund=move_type in (
                                                                                          'out_refund', 'in_refund'),
                                                                                      users=no_of_users)
            total = taxes_res['total_excluded']
            tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
            res['price_subtotal'] = total
            res['price_total'] = (total + tax_amount)
            print("ressssssssssssssssssssssssssss  :", total, total + tax_amount)
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res


class AccountTax(models.Model):
    _inherit = 'account.tax'
    """Inherited to override tax calculation methode"""

    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None,
                    is_refund=False,
                    handle_price_include=True, users=1.0):
        if not self:
            company = self.env.company
        else:
            company = self[0].company_id

        taxes, groups_map = self.flatten_taxes_hierarchy(create_map=True)
        base_excluded_flag = False  # price_include=False && include_base_amount=True
        included_flag = False  # price_include=True
        for tax in taxes:
            if tax.price_include:
                included_flag = True
            elif tax.include_base_amount:
                base_excluded_flag = True
            if base_excluded_flag and included_flag:
                raise UserError(_(
                    'Unable to mix any taxes being price included with taxes affecting the base amount but not included in price.'))

        if not currency:
            currency = company.currency_id
        prec = currency.rounding

        round_tax = False if company.tax_calculation_rounding_method == 'round_globally' else True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])

        if not round_tax:
            prec *= 1e-5

        def recompute_base(base_amount, fixed_amount, percent_amount, division_amount):

            return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100

        # print("price_unit : ", price_unit, quantity, users)
        base = currency.round(price_unit * quantity * users)
        print("\nusersssssssssssssss\n",users)

        sign = 1
        if currency.is_zero(base):
            sign = self._context.get('force_sign', 1)
        elif base < 0:
            sign = -1
        if base < 0:
            base = -base

        total_included_checkpoints = {}
        i = len(taxes) - 1
        store_included_tax_total = True
        # Keep track of the accumulated included fixed/percent amount.
        incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
        # Store the tax amounts we compute while searching for the total_excluded
        cached_tax_amounts = {}
        if handle_price_include:
            for tax in reversed(taxes):
                tax_repartition_lines = (
                        is_refund
                        and tax.refund_repartition_line_ids
                        or tax.invoice_repartition_line_ids
                ).filtered(lambda x: x.repartition_type == "tax")
                sum_repartition_factor = sum(tax_repartition_lines.mapped("factor"))

                if tax.include_base_amount:
                    base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount)
                    incl_fixed_amount = incl_percent_amount = incl_division_amount = 0
                    store_included_tax_total = True
                if tax.price_include or self._context.get('force_price_include'):
                    if tax.amount_type == 'percent':
                        incl_percent_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'division':
                        incl_division_amount += tax.amount * sum_repartition_factor
                    elif tax.amount_type == 'fixed':
                        incl_fixed_amount += quantity * users * tax.amount * sum_repartition_factor
                    else:
                        # tax.amount_type == other (python)
                        tax_amount = tax._compute_amount(base, sign * price_unit, quantity, product,
                                                         partner) * sum_repartition_factor
                        incl_fixed_amount += tax_amount
                        # Avoid unecessary re-computation
                        cached_tax_amounts[i] = tax_amount
                    # In case of a zero tax, do not store the base amount since the tax amount will
                    # be zero anyway. Group and Python taxes have an amount of zero, so do not take
                    # them into account.
                    if store_included_tax_total and (
                            tax.amount or tax.amount_type not in ("percent", "division", "fixed")
                    ):
                        total_included_checkpoints[i] = base
                        store_included_tax_total = False
                i -= 1

        total_excluded = currency.round(
            recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount))

        base = total_included = total_void = total_excluded

        taxes_vals = []
        i = 0
        cumulated_tax_included_amount = 0
        for tax in taxes:
            tax_repartition_lines = (
                    is_refund and tax.refund_repartition_line_ids or tax.invoice_repartition_line_ids).filtered(
                lambda x: x.repartition_type == 'tax')
            sum_repartition_factor = sum(tax_repartition_lines.mapped('factor'))
            price_include = self._context.get('force_price_include', tax.price_include)

            # compute the tax_amount
            if price_include and total_included_checkpoints.get(i):
                # We know the total to reach for that tax, so we make a substraction to avoid any rounding issues
                tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount)
                cumulated_tax_included_amount = 0
            else:
                tax_amount = tax.with_context(force_price_include=False)._compute_amount(
                    base, sign * price_unit, quantity, product, partner)

            # Round the tax_amount multiplied by the computed repartition lines factor.
            tax_amount = round(tax_amount, precision_rounding=prec)
            factorized_tax_amount = round(tax_amount * sum_repartition_factor, precision_rounding=prec)

            if price_include and not total_included_checkpoints.get(i):
                cumulated_tax_included_amount += factorized_tax_amount

            # If the tax affects the base of subsequent taxes, its tax move lines must
            # receive the base tags and tag_ids of these taxes, so that the tax report computes
            # the right total
            subsequent_taxes = self.env['account.tax']
            subsequent_tags = self.env['account.account.tag']
            if tax.include_base_amount:
                subsequent_taxes = taxes[i + 1:]
                subsequent_tags = subsequent_taxes.get_tax_tags(is_refund, 'base')

            # Compute the tax line amounts by multiplying each factor with the tax amount.
            # Then, spread the tax rounding to ensure the consistency of each line independently with the factorized
            # amount. E.g:
            #
            # Suppose a tax having 4 x 50% repartition line applied on a tax amount of 0.03 with 2 decimal places.
            # The factorized_tax_amount will be 0.06 (200% x 0.03). However, each line taken independently will compute
            # 50% * 0.03 = 0.01 with rounding. It means there is 0.06 - 0.04 = 0.02 as total_rounding_error to dispatch
            # in lines as 2 x 0.01.
            repartition_line_amounts = [round(tax_amount * line.factor, precision_rounding=prec) for line in
                                        tax_repartition_lines]
            total_rounding_error = round(factorized_tax_amount - sum(repartition_line_amounts), precision_rounding=prec)
            nber_rounding_steps = int(abs(total_rounding_error / currency.rounding))
            rounding_error = round(nber_rounding_steps and total_rounding_error / nber_rounding_steps or 0.0,
                                   precision_rounding=prec)

            for repartition_line, line_amount in zip(tax_repartition_lines, repartition_line_amounts):

                if nber_rounding_steps:
                    line_amount += rounding_error
                    nber_rounding_steps -= 1

                taxes_vals.append({
                    'id': tax.id,
                    'name': partner and tax.with_context(lang=partner.lang).name or tax.name,
                    'amount': sign * line_amount,
                    'base': round(sign * base, precision_rounding=prec),
                    'sequence': tax.sequence,
                    'account_id': tax.cash_basis_transition_account_id.id if tax.tax_exigibility == 'on_payment' else repartition_line.account_id.id,
                    'analytic': tax.analytic,
                    'price_include': price_include,
                    'tax_exigibility': tax.tax_exigibility,
                    'tax_repartition_line_id': repartition_line.id,
                    'group': groups_map.get(tax),
                    'tag_ids': (repartition_line.tag_ids + subsequent_tags).ids,
                    'tax_ids': subsequent_taxes.ids,
                })

                if not repartition_line.account_id:
                    total_void += line_amount

            # Affect subsequent taxes
            if tax.include_base_amount:
                base += factorized_tax_amount

            total_included += factorized_tax_amount
            i += 1
        print('taxes : ___________', taxes_vals)
        return {
            'base_tags': taxes.mapped(
                is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids').filtered(
                lambda x: x.repartition_type == 'base').mapped('tag_ids').ids,
            'taxes': taxes_vals,
            'total_excluded': sign * total_excluded,
            'total_included': sign * currency.round(total_included),
            'total_void': sign * currency.round(total_void),
        }
