from odoo import fields, api, models, _
from odoo.exceptions import UserError, ValidationError
import erppeek
import logging
import os
import subprocess
import xmlrpc
from odoo.http import request
from odoo.tools import config, odoo
import logging
import odoo

from odoo.api import Environment
from odoo.service import db

_logger = logging.getLogger(__name__)
ADMINUSER_ID = 2


# from erppeek import Client


class bareTenantModuleInstall(models.TransientModel):
    _name = 'bare.tenant.module.install'
    _description = '''For Display All Installed and Uninstalled Modules'''

    bare_tenant_db = fields.Char(string='Bare Tenant DB', readonly="true")
    installed_moduels = fields.One2many('installed.modules.bare.tenant', 'bare_tenant_module_id',
                                        string="Installed Modules")
    uninstalled_modules = fields.One2many('uninstalled.modules.bare.tenant', 'bare_tenant_module_id',
                                          string='Uninstalled Modules')

    @api.model
    def default_get(self, fields_list):
        res = super(bareTenantModuleInstall, self).default_get(fields_list)

        # Unlink first all Transiant models
        self.env['installed.modules.bare.tenant'].search([]).unlink()
        self.env['uninstalled.modules.bare.tenant'].search([]).unlink()
        self.uninstalled_modules.unlink()
        self.installed_moduels.unlink()

        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update({'bare_tenant_db': ICPSudo.search([('key', '=', 'bare_tenant_db')]).value})
        # self.load_modules(res)

        con = self.conDBxmlrpc()
        i_modules = self.load_all_modules(con, 'installed')
        u_modules = self.load_all_modules(con, 'uninstalled')
        res.update({'installed_moduels': i_modules})
        res.update({'uninstalled_modules': u_modules})

        return res

    #
    # # Erppeek Library
    # def bare_tenant_db_connection(self):  # Connet to Bare Tenant Database
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     server = ICPSudo.get_param('web.base.url')
    #     db = ICPSudo.get_param('bare_tenant_db')
    #     user = ICPSudo.get_param('bare_admin_user')
    #     pwd = ICPSudo.get_param('bare_admin_pass')
    #     ODOO_CONF = ICPSudo.get_param('odoorc_path')
    #     if ODOO_CONF:
    #         config = odoo.tools.config
    #         config['load_language'] = request.env.lang
    #         odoo.tools.config.parse_config(['--config=%s' % ODOO_CONF])
    #         try:
    #             con = erppeek.Client(server,
    #                                  db=db,
    #                                  user=user,  # admin
    #                                  password=pwd,  # admin
    #                                  transport=None, verbose=False)
    #         except Exception as e:
    #             _logger.exception("Exception of Connection for with Bare Tenant DB: %s.\n Original Traceback:\n%s", e)
    #             con = False
    #             pass
    #     else:
    #         raise UserError(_("Please Enter Path of Odoorc file for Bare Tenant"))
    #     return con

    #
    # def load_modules(self, res):
    #     con = self.bare_tenant_db_connection()
    #     if con:
    #         installed_modules = con.read('ir.module.module', [('state', '=', 'installed')],
    #                                      fields=('name', 'shortdesc', 'state'),
    #                                      offset=0, limit=None, order=None, context=None)
    #         i_modules = []
    #         for module in installed_modules:
    #             i_modules.append((0, 0, {'bare_tenant_module_id': module['id'],
    #                                      'module_name': module['shortdesc'],
    #                                      'technical_name': module['name'],
    #                                      'status': module['state']
    #                                      }))
    #             res.update({'installed_moduels': i_modules})
    # 
    #         uninstalled_moduels = con.read('ir.module.module', [('state', '=', 'uninstalled')],
    #                                        fields=('name', 'shortdesc', 'state'),
    #                                        offset=0, limit=None, order=None, context=None)
    #         u_modules = []
    #         for module in uninstalled_moduels:
    #             u_modules.append((0, 0, {'bare_tenant_module_id': module['id'],
    #                                      'module_name': module['shortdesc'],
    #                                      'technical_name': module['name'],
    #                                      'status': module['state']
    #                                      }))
    # 
    #             res.update({'uninstalled_modules': u_modules})
    #     else:
    #         raise UserError(_(" Unsuccessful Connection with Bare Tenant DB."))

    def install_modules(self):
        context = self._context.copy()
        data = self.conDBxmlrpc()  # connect to database with xmlrpc
        if data:
            try:
                xmlrpc_obj = data['obj']
                if context['action'] == 'Install':
                    objects = self.env['uninstalled.modules.bare.tenant'].search([('bool_checkbox', '=', True)])
                    if objects:
                        try:
                            for uin_object in objects:
                                res_ids = xmlrpc_obj.execute(
                                    data['db'], data['uid'], data['pwd'],
                                    'ir.module.module', 'search', [('name', '=', uin_object.technical_name)])
                                if len(res_ids) != 1:
                                    raise Exception("Search failed")
                                # install the module
                                xmlrpc_obj.execute(data['db'], data['uid'], data['pwd'],
                                                   'ir.module.module', "button_immediate_install", res_ids)
                        except Exception as e:
                            print(e)
                            pass

                elif context['action'] == 'Uninstall':
                    objects2 = self.env['installed.modules.bare.tenant'].search([('bool_chk', '=', True)])
                    # con = self.bare_tenant_db_connection()
                    try:
                        for in_object in objects2:
                            res_ids = xmlrpc_obj.execute(
                                data['db'], data['uid'], data['pwd'],
                                'ir.module.module', 'search', [('name', '=', in_object.technical_name)])
                            if len(res_ids) != 1:
                                raise Exception("Search failed")
                            # Uninstall the module
                            xmlrpc_obj.execute(data['db'], data['uid'], data['pwd'],
                                               'ir.module.module', "button_immediate_uninstall", res_ids)
                    except Exception as e:
                        print(e)
                        pass

            except Exception as e:
                print(e)
                _logger.exception('Exception: %s', e)
                # raise UserError(_('Access Right Error'))
                pass
        else:
            raise UserError(_(" Unsuccessful Connection with Bare Tenant DB."))

    def load_all_modules(self, con, state):  ###########
        if con:
            xmlrpc_obj = con['obj']
            update_app_list = xmlrpc_obj.execute_kw(con['db'], con['uid'], con['pwd'],
                                                    'ir.module.module', 'update_list', [])
            ids = xmlrpc_obj.execute(con['db'], con['uid'], con['pwd'],
                                     'ir.module.module', 'search', [('state', '=', state)])
            all_modules = xmlrpc_obj.execute_kw(con['db'], con['uid'], con['pwd'],
                                                'ir.module.module', 'read',
                                                [ids], {'fields': ['name', 'shortdesc', 'state']})
            ret = []
            for module in all_modules:
                ret.append((0, 0, {'bare_tenant_module_id': module['id'],
                                   'module_name': module['shortdesc'],
                                   'technical_name': module['name'],
                                   'status': module['state']
                                   }))
            return ret
        else:
            raise UserError(_(" Unsuccessful Connection with Bare Tenant DB."))

    def conDBxmlrpc(self, bare_old_pass=None):

        ICPSudo = self.env['ir.config_parameter'].sudo()
        port = ICPSudo.get_param('odoorc_port')
        db = ICPSudo.get_param('bare_tenant_db')
        user = ICPSudo.get_param('bare_admin_user')
        if bare_old_pass:
            pwd = str(bare_old_pass)
        else:
            pwd = ICPSudo.get_param('bare_admin_pass')
        _logger.info("Started For Some Activity for Bare Tenant Db on this "
                     "port________________________________________%s" % port)
        # 318859a0156669eaa1b65e96ceab90a3188ec621 api key
        server_ip = ICPSudo.get_param('bare_tenant_ip')
        if not server_ip:
            raise ValidationError('Please Enter Valid ServerIPAddress of Database')

        server = 'http://{}:{}'.format(server_ip, port)
        print("\n\n\nserver : ", server, "user : ", user, 'pwd :', pwd, 'db :', db)

        if server:
            try:
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(server))
                uid = common.authenticate(db, user, pwd, {})
                models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(server))
                data = {'uid': uid, 'db': db, 'user': user, 'pwd': pwd, 'obj': models}
            except Exception as e:
                # data = False
                _logger.exception('Exception: %s', e)
                raise UserError(_('Bare Connection Refused '))  # %s') % server
        else:
            # data = False
            raise UserError(_("Please Enter url with port in Bare Tenant configuration"))
        return data
