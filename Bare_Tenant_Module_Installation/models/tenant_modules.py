import odoo
from odoo import api, models, fields, _

import xmlrpc
import erppeek
from odoo.exceptions import UserError, ValidationError

import logging

from odoo.http import request

_logger = logging.getLogger(__name__)


class TenantModulesList(models.TransientModel):
    _name = 'tenant.module.list'
    _description = "It Shows All tenenat modules list which are installed or uninstalled"

    tenant_db = fields.Char(string='Tenant DB', readonly=True)
    installed_moduels = fields.One2many('installed.modules.on.tenant', 'tenant_module_id',
                                        string="Installed Modules")
    uninstalled_modules = fields.One2many('uninstalled.modules.on.tenant', 'tenant_module_id',
                                          string='Uninstalled Modules')

    @api.model
    def default_get(self, fields_list):
        res = super(TenantModulesList, self).default_get(fields_list)
        active_id = self._context.get('current_id')
        obj = self.env['tenant.database.list'].browse(int(active_id))
        res.update({'tenant_db': obj.name})

        # Unlink first all Transiant models
        self.env['installed.modules.on.tenant'].search([]).unlink()
        self.env['uninstalled.modules.on.tenant'].search([]).unlink()
        self.uninstalled_modules.unlink()
        self.installed_moduels.unlink()

        con = self.tenant_db_connection(active_id)
        i_modules = self.load_all_modules(con, 'installed')
        u_modules = self.load_all_modules(con, 'uninstalled')
        res.update({'installed_moduels': i_modules})
        res.update({'uninstalled_modules': u_modules})
        return res

    def load_all_modules(self, con, state):
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
                ret.append((0, 0, {'tenant_module_id': module['id'],
                                   'module_name': module['shortdesc'],
                                   'technical_name': module['name'],
                                   'status': module['state']
                                   }))
            return ret
        else:
            raise UserError(_(" Unsuccessful Connection with Bare Tenant DB."))

    def module_activity(self):
        context = self._context.copy()
        active_id = self._context.get('current_id')
        data = self.tenant_db_connection(active_id)  # connect to database with xmlrpc
        if data:
            try:
                xmlrpc_obj = data['obj']
                if context['action'] == 'Install':
                    objects = self.env['uninstalled.modules.on.tenant'].search([('bool_checkbox', '=', True)])
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
                            _logger.exception(e)
                            pass

                elif context['action'] == 'Uninstall':
                    objects2 = self.env['installed.modules.on.tenant'].search([('bool_chk', '=', True)])
                    try:
                        for in_object in objects2:
                            res_ids = xmlrpc_obj.execute(
                                data['db'], data['uid'], data['pwd'],
                                'ir.module.module', 'search', [('name', '=', in_object.technical_name)])
                            if len(res_ids) != 1:
                                raise Exception("Search failed")
                            # # Uninstall the module
                            xmlrpc_obj.execute_kw(data['db'], data['uid'], data['pwd'],
                                                  'ir.module.module', "button_immediate_uninstall", res_ids,
                                                  {'context': {'uid': data[
                                                      'uid']}})  # Passed uid for authentication for uninstallation
                    except Exception as e:
                        print(e)
                        pass

            except Exception as e:
                print(e)
                # _logger.exception('Exception: %s', e)
                raise UserError(_('Access Right Error %s'))
                pass
        else:
            raise UserError(_(" Unsuccessful Connection with Bare Tenant DB."))

    def tenant_db_connection(self, active_id):
        TConf = self.env['tenant.database.list'].browse(int(active_id))
        #       '___________________________________Active ids records')
        ICPSudo = self.env['ir.config_parameter'].sudo()
        data = False
        port = ICPSudo.get_param('odoorc_port')
        db = TConf.name
        user = TConf.super_user_login
        pwd = TConf.super_user_pwd
        # 318859a0156669eaa1b65e96ceab90a3188ec621 api key
        server_ip = ICPSudo.get_param('bare_tenant_ip')
        if not server_ip:
            raise ValidationError('Please Enter Valid ServerIPAddress of Database')
        server = 'http://{}:{}'.format(server_ip, port)

        if server:
            try:
                common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(server))
                uid = common.authenticate(db, user, pwd, {})
                xmlrpc_obj = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(server))
                data = {'uid': uid, 'db': db, 'user': user, 'pwd': pwd, 'obj': xmlrpc_obj}
                _logger.info(
                    "Started For Some Activity On Tenant db on this port____________________________%s" % server)
            except Exception as e:
                data = False
                _logger.exception('Exception: %s', e)
                raise UserError(_('Bare Connection Refused '))
        else:
            raise UserError(_("Please Enter Port in Bare Tenant configuration"))
        return data


class TenantDBList(models.Model):
    _inherit = "tenant.database.list"

    isdeactivated = fields.Boolean(related="stage_id.is_deactivated", default=False)
    isterminated = fields.Boolean(related="stage_id.is_purge", default=False)
