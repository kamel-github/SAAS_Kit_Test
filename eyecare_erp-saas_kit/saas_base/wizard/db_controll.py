# -*- coding: utf-8 -*-
from odoo import api, fields, models
import psycopg2
from odoo import exceptions
from odoo.exceptions import UserError, ValidationError
import odoo
import datetime
from odoo.tools.translate import _
from odoo import SUPERUSER_ID, api
from odoo import sql_db, _
from odoo.tools import config
from odoo.service import db
import xmlrpc
from datetime import datetime
from contextlib import closing
import traceback
import logging

ADMINUSER_ID = 2
_logger = logging.getLogger(__name__)


class db_controll_wizard(models.TransientModel):
    """ Manually Deactivating the database"""
    _name = 'deactive_db.wizard'
    _description = 'Expire Database'

    db_name = fields.Many2one('tenant.database.list', 'Select Database', required=True)
    reason = fields.Text('Reason')

    #     def cancel(self,cr,uid,ids,conText=None):
    #         return { 'type':'ir.actions.act_window_close' }
    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def expire_db(self):
        _logger.info('SaaS-Db Expire db check start')
        cr = self._cr

        # Find all databases list available
        server_db_list = []
        cr.execute("select datname from pg_database where datistemplate=false")
        cr_res = cr.fetchall()
        for item in cr_res:
            if item:
                server_db_list.append(item[0])

        tenant_db = self.db_name
        exp_date = tenant_db.exp_date
        user_id = self._uid
        reason = self.reason
        if tenant_db.name in server_db_list:
            # print('Current Database : ', tenant_db)
            ICPSudo = self.env['ir.config_parameter'].sudo()
            # Pulled outside of this if statement and if statement commented
            # ==========================Start=============================================
            # check tenant database is in free trail or not

            # check if db state in [active,grace]
            in_allowed_stages = False
            if tenant_db.stage_id.is_active or tenant_db.stage_id.is_grace:
                in_allowed_stages = True

            if in_allowed_stages:
                # if today is expire date then generate the invoice
                # Check id database expiry date is increased from todays date
                stage_ids = self.env['tenant.database.stage'].search([('is_expired', '=', True)], limit=1)
                tenant_db.write({'stage_id': stage_ids.id if stage_ids else False})

                # cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': tenant_db.name,
                #                                                         'role': 'expired_db_owner'})

                tenant_db.write({'expired': True,
                                 'user_id': user_id,
                                 'reason': reason,
                                 'exp_date': exp_date,
                                 'deactivated_date': datetime.now().strftime('%Y-%m-%d'),
                                 'stage_id': stage_ids[0].id if stage_ids else False})

                brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
                brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
                brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
                db_name = tenant_db.name
                dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
                uid_dst = common.authenticate(db_name, brand_admin, brand_pwd, {})
                db_expire = dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'db.expire', 'search', [[]])
                # print("db_expire : ", db_expire)
                for msg in db_expire:
                    # print("msg : ", msg)
                    dest_model.execute_kw(db_name, uid_dst, brand_pwd, 'db.expire', 'write',
                                          [msg,
                                           {
                                               'db_expire': True,
                                           }]
                                          )
                tenant_db.send_saas_alert_email('expired')
        else:
            raise ValidationError(_('This database is terminated or dropped.'))

        cr.commit()
        return {
            'view_type': 'kanban',
            'view_mode': 'kanban',
            'res_model': 'tenant.database.list',
            'type': 'ir.actions.act_window',
        }

    #     def activate_db(self, cr, uid, ids, data, conText=None):
    #         config = odoo.tools.config
    #         tenant_db_list_obj = self.pool.get('tenant.database.list')
    #         tenant_db = self.browse(cr,uid,ids)[0].db_name
    #         db_name = self.browse(cr,uid,ids)[0].db_name.name
    #         expiry_date_str = str(self.browse(cr,uid,ids)[0].db_name.exp_date).split("-")
    #         exp_date = datetime(int(expiry_date_str[0]),int(expiry_date_str[1]),int(expiry_date_str[2]))
    #         today = datetime.today()
    #         if exp_date > today:
    #             try : cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s"%{'db':db_name ,'role':config['db_user']})
    #             except Exception as e:
    #                 raise osv.except_osv(_('Error!'), _(e))
    #
    #             stage_ids = self.pool.get('tenant.database.stage').search(cr, uid, [('is_active', '=', True)])
    #             tenant_db_list_obj.write(cr,uid,[tenant_db.id],{'expired':False,
    #                                                             'stage_id':stage_ids[0] if stage_ids else False})
    #             cr.commit()
    #         else :
    #             raise osv.except_osv(_('Warning!'), _('Sorry, you can not activate the Database...!'))
    #         return{
    #           'view_type': 'kanban',
    #           'view_mode': 'kanban',
    #           'res_model': 'tenant.database.list',
    #           'conText': conText,
    #           'type': 'ir.actions.act_window',
    #           }


    def activate_db(self):

        grace_period = self.env['tenant.database.stage'].search([('is_grace', '=', True)])
        active_stage = self.env['tenant.database.stage'].search([('is_active', '=', True)])
        tenant_db = self.db_name
        # print(tenant_db.stage_id.id,'  =  ',grace_period[0].id)
        # ACTIVATE DATABASE WHICH ARE IN GRACE PERIOD DIRECTLY
        if tenant_db.stage_id.id == grace_period[0].id:

            import datetime
            from dateutil.relativedelta import relativedelta
            months_to_add = 0
            term_type = tenant_db.sale_order_ref.invoice_term_id.type
            if term_type == 'from_first_date': months_to_add = 1
            if term_type == 'quarter': months_to_add = 3
            if term_type == 'half_year': months_to_add = 6
            if term_type == 'year': months_to_add = 12

            new_exp_date = str(
                datetime.datetime.strptime(str(tenant_db.exp_date), '%Y-%m-%d') + relativedelta(
                    months=+months_to_add))[:10]
            # print(active_stage,'-----------',new_exp_date, '__________',months_to_add)

            tenant_db.write({
                'stage_id': active_stage[0].id,
                'exp_date': new_exp_date,
            })
            return {
                'view_type': 'kanban',
                'view_mode': 'kanban',
                'res_model': 'tenant.database.list',
                'context': self._context,
                'type': 'ir.actions.act_window',
            }

        saas_db_name = self.env.cr.dbname
        db = sql_db.db_connect(saas_db_name)
        with closing(db.cursor()) as cr:
            cmd = "SELECT d.datname as saasmaster,pg_catalog.pg_get_userbyid(d.datdba) as Owner FROM pg_catalog.pg_database d;"
            cr.execute(cmd)
            rows = cr.fetchall()
        owner = None
        for row in rows:  # Getting Saasmaster_v13 owner
            if row[0] == saas_db_name:
                owner = row[1]
        tenant_db = self.db_name
        cr = self._cr
        db_name = self.db_name.name
        expiry_date_str = str(self.db_name.exp_date).split("-")
        exp_date = datetime(int(expiry_date_str[0]), int(expiry_date_str[1]), int(expiry_date_str[2]))
        today = datetime.today()
        # if exp_date > today:
        try:
            cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': db_name, 'role': owner})
        except Exception as e:
            raise exceptions.except_orm(_("Error!"), _(e))

        stage_ids = self.env['tenant.database.stage'].search([('is_active', '=', True)])
        tenant_db.write({'expired': False,
                         'stage_id': stage_ids[0].id if stage_ids else False})
        cr.commit()
        # else:
        #     raise UserError(_('You cant activate the expired Database'))
        return {
            'view_type': 'kanban',
            'view_mode': 'kanban',
            'res_model': 'tenant.database.list',
            'context': self._context,
            'type': 'ir.actions.act_window',
        }

    def terminate_db(self):
        """
        1. Set tenant DB stage to Purge
        2. Inactive all agreements related to this db
        3. Drop the DB
        """
        config = odoo.tools.config
        tenant_db_list_obj = self.env['tenant.database.list'].sudo()
        agreement_obj = self.env['sale.recurring.orders.agreement'].sudo()

        tenant_db = self.db_name
        db_name = self.db_name.name
        db_id = self.db_name.id
        cr = self._cr
        ##deactivate DB
        stage_ids = self.env['tenant.database.stage'].search([('is_purge', '=', True)])
        tenant_db.write({'stage_id': stage_ids[0].id if stage_ids else False})
        ##deactivate agreements
        agreement_ids = agreement_obj.search([('order_line.order_id.instance_name', '=', str(db_name))])

        agreement_ids.write({'active': False})

        # cr.execute("""UPDATE pg_database SET datallowconn = 'false' WHERE datname = '%s';"""%db_name)
        # cr.execute("""ALTER DATABASE %s CONNECTION LIMIT 1;"""%db_name)

        cr.execute("""SELECT pg_terminate_backend(pid) 
 FROM pg_stat_get_activity(NULL::integer) 
 WHERE datid=(SELECT oid from pg_database where datname = '%s');""" % db_name)

        cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': tenant_db.name, 'role': 'expired_db_owner'})

        return {
            'view_type': 'kanban',
            'view_mode': 'kanban',
            'res_model': 'tenant.database.list',
            'context': self._context,
            'type': 'ir.actions.act_window',
        }

        ##Don't drop Database, just move to Terminated stage

        ##drop DB
        try:
            cr.execute("ALTER DATABASE %(db)s OWNER TO %(role)s" % {'db': db_name, 'role': config['db_user']})
        except Exception as e:
            trace_str = str(traceback.format_exc())
            raise exceptions.except_orm(_("Error!"), _(str(e) + "\n " + trace_str))



        db = odoo.sql_db.db_connect('postgres')
        with closing(db.cursor()) as cr:
            cr.autocommit(True)  # To avoid transaction block
            # _drop_conn(cr, db_name)

            # Try to terminate all other connections that might prevent
            # dropping the database
            try:
                pid_col = 'pid' if cr._cnx.server_version >= 90200 else 'procpid'

                #                 cr.execute("""SELECT pg_terminate_backend(%(pid_col)s)
                #                               FROM pg_stat_activity
                #                               WHERE datname = %%s AND
                #                                     %(pid_col)s != pg_backend_pid()""" % {'pid_col': pid_col},
                #                            (db_name,))
                #                 cr.execute("""select pg_terminate_backend(pid) from pg_stat_activity where datname='%s';"""%(db_name,))

                cr.execute("""UPDATE pg_database SET datallowconn = 'false' WHERE datname = '%s';""" % db_name)
                cr.execute("""ALTER DATABASE %s CONNECTION LIMIT 1;""" % db_name)

                cr.execute("""SELECT pg_terminate_backend(pid) 
 FROM pg_stat_get_activity(NULL::integer) 
 WHERE datid=(SELECT oid from pg_database where datname = '%s');""" % db_name)

                cr.execute("DROP DATABASE %s" % db_name)
            except Exception as e:
                trace_str = str(traceback.format_exc())
                raise Exception("Couldn't drop database %s: %s" % (db_name, str(e) + "\n\n" + trace_str))


        # db.exp_drop(db_name)
        return {
            'view_type': 'kanban',
            'view_mode': 'kanban',
            'res_model': 'tenant.database.list',
            'context': self._context,
            'type': 'ir.actions.act_window',
        }


# (db_controll_wizard)

class update_tenants(models.TransientModel):
    _name = 'update.tenants.wizard'
    _description = 'Update Tenants stages'

    #     def update_tenants(self, cr, uid, ids, data, conText=None):
    #         tenant_db_list_obj = self.pool.get('tenant.database.list')
    #         tenant_ids = tenant_db_list_obj.search(cr, uid, [('stage_id', '=', False)])
    #         for tenant in tenant_db_list_obj.browse(cr, uid, tenant_ids):
    #             if tenant.free_trial:
    #                 active_stage_id = self.pool.get('tenant.database.stage').search(cr, uid, [('is_active', '=', True)])
    #                 tenant_db_list_obj.write(cr, uid, [tenant.id], {'stage_id':active_stage_id[0] if active_stage_id else False}, conText)
    #
    #             if tenant.expired:
    #                 active_stage_id = self.pool.get('tenant.database.stage').search(cr, uid, [('is_expired', '=', True)])
    #                 tenant_db_list_obj.write(cr, uid, [tenant.id], {'stage_id':active_stage_id[0] if active_stage_id else False}, conText)
    #
    #         return { 'type':'ir.actions.act_window_close' }
    #
    def update_tenants(self):
        tenant_db_list_obj = self.env['tenant.database.list']
        tenant_ids = tenant_db_list_obj.search([('stage_id', '=', False)])
        for tenant in tenant_ids:
            if tenant.free_trial:
                active_stage_id = self.env['tenant.database.stage'].search([('is_active', '=', True)], limit=1)
                tenant.write({'stage_id': active_stage_id.id if active_stage_id else False})

            if tenant.expired:
                active_stage_id = self.env['tenant.database.stage'].search([('is_expired', '=', True)], limit=1)
                tenant.write({'stage_id': active_stage_id.id if active_stage_id else False})

        return {'type': 'ir.actions.act_window_close'}
