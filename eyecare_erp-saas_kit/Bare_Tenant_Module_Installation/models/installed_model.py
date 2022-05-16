from odoo import api, fields, models
import os
from odoo.exceptions import UserError


class InstalledModulesOnBareTenant(models.TransientModel):
    _name = "installed.modules.bare.tenant"
    _description = '''store All Installed Moudles from db'''

    bare_tenant_module_id = fields.Many2one('bare.tenant.module.install', string="module Id")
    bool_chk = fields.Boolean(default=False, string="Check", store=True)
    module_name = fields.Char('Module Name')
    technical_name = fields.Char('Module Technical Name')
    status = fields.Selection([('installed', 'Installed'),
                               ('uninstalled', 'Uninstalled'),
                               ('uninstallable', 'Uninstallable'),
                               ('to upgrade', 'To be Upgrade'),
                               ('to remove', 'To be Remove'),
                               ('to install', 'To be Install')])

    def unlink(self):
        res = super(InstalledModulesOnBareTenant, self).unlink()
        return res


class UninstalledModulesOnBareTenant(models.TransientModel):
    _name = "uninstalled.modules.bare.tenant"
    _description = '''store All UnInstalled Moudles from db'''

    bare_tenant_module_id = fields.Many2one('bare.tenant.module.install', string="module Id")
    # bare_tenant_module_id = fields.Char(string="module Id")
    bool_checkbox = fields.Boolean('Check')
    module_name = fields.Char('Module Name')
    technical_name = fields.Char('Module Technical Name')
    status = fields.Selection([('installed', 'Installed'),
                               ('uninstalled', 'Uninstalled'),
                               ('uninstallable', 'Uninstallable'),
                               ('to upgrade', 'To be Upgrade'),
                               ('to remove', 'To be Remove'),
                               ('to install', 'To be Install')])

    def unlink(self):
        res = super(UninstalledModulesOnBareTenant, self).unlink()
        return res


# /////////////////////////////////////////////////////////////////////

class InstalledModulesOnTenant(models.TransientModel):
    _name = "installed.modules.on.tenant"
    _description = '''store All Installed Moudles from db'''

    tenant_module_id = fields.Many2one('tenant.module.list', string="module Id")
    bool_chk = fields.Boolean("Check")
    module_name = fields.Char('Module Name')
    technical_name = fields.Char('Module Technical Name')
    status = fields.Selection([('installed', 'Installed'),
                               ('uninstalled', 'Uninstalled'),
                               ('uninstallable', 'Uninstallable'),
                               ('to upgrade', 'To be Upgrade'),
                               ('to remove', 'To be Remove'),
                               ('to install', 'To be Install')])

    def unlink(self):
        res = super(InstalledModulesOnTenant, self).unlink()
        return res


class UninstalledModulesOnTenant(models.TransientModel):
    _name = "uninstalled.modules.on.tenant"
    _description = '''store All UnInstalled Moudles from db'''

    tenant_module_id = fields.Many2one('tenant.module.list', string="module Id")

    bool_checkbox = fields.Boolean('Check')
    module_name = fields.Char('Module Name')
    technical_name = fields.Char('Module Technical Name')
    status = fields.Selection([('installed', 'Installed'),
                               ('uninstalled', 'Uninstalled'),
                               ('uninstallable', 'Uninstallable'),
                               ('to upgrade', 'To be Upgrade'),
                               ('to remove', 'To be Remove'),
                               ('to install', 'To be Install')])

    def unlink(self):
        res = super(UninstalledModulesOnTenant, self).unlink()
        return res


class inheritResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _description = "Path for odoorc file for bare tenant"

    bare_admin_user = fields.Char(string='Bare Admin Login', required=True)
    bare_admin_pass = fields.Char(string='Bare Admin Password', required=True)
    bare_old_admin_pass = fields.Char(string='Bare Old Admin Password')
    odoorc_path = fields.Char(string='Bare Tenant Odoorc Path', config_parameter="bare_rc_path", help="Provide Odoorc "
                                                                                                      "Path for Bare "
                                                                                                      "tenant db Module "
                                                                                                      "installation / "
                                                                                                      "Uninstallation")
    odoorc_port = fields.Char(string='Bare Tenant Port', help="9050")
    bare_tenant_ip = fields.Char(string='Bare Tenant Server', default="http://127.0.0.1", help="Bare Tenant Server")

    def start_server_port(self):
        os.system('./odoo-bin --xmlrpc-port 8014')

    @api.model
    def default_get(self, fields_list):
        res = super(inheritResConfigSettings, self).default_get(fields_list)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        values = {
            'odoorc_path': ICPSudo.search([('key', '=', 'odoorc_path')]).value,
            'odoorc_port': ICPSudo.search([('key', '=', 'odoorc_port')]).value,
            'bare_admin_user': ICPSudo.search([('key', '=', 'bare_admin_user')]).value,
            'bare_admin_pass': ICPSudo.search([('key', '=', 'bare_admin_pass')]).value,
            'bare_tenant_ip': ICPSudo.search([('key', '=', 'bare_tenant_ip')]).value,
            'bare_old_admin_pass': ICPSudo.search([('key', '=', 'bare_old_admin_pass')]).value,
        }
        res.update(values)

        return res

    # @api.constrains('admin_pwd')
    def update_tenant_admin_password(self):
        password = str(self.admin_pwd)
        tenants = self.env['tenant.database.list'].sudo().search([])
        for tenant in tenants:
            if tenant.stage_id.is_active or tenant.stage_id.is_grace:
                try:
                    # print('---------->Name  ', tenant.name, '--------------> Admin Pwd : ', password)
                    data = self.env['tenant.module.list'].tenant_db_connection(tenant.id)
                    tenant.write({'super_user_pwd': password})
                    dest_model = data['obj']

                    dest_model.execute_kw(data['db'], data['uid'], data['pwd'], 'res.users', 'write',
                                          [2, {'password': password or 'admin',}])

                    # print('---------->xmlrpc_object ', data)
                except Exception as e:
                    print('\n\nError : \n\n%s' %e)
                    pass

    def update_bare_admin_password(self):
        try:
            data = self.env['bare.tenant.module.install'].conDBxmlrpc(bare_old_pass=self.bare_old_admin_pass)
            dest_model = data['obj']
            dest_model.execute_kw(data['db'], data['uid'], data['pwd'], 'res.users', 'write',
                                  [2, {'password': str(self.bare_admin_pass) or 'admin', }])
            self.set_configs('bare_old_admin_pass', str(self.bare_admin_pass) or "admin")
        except Exception as e:
            print('Error : %s'%e)
            raise UserError('Error : %s '% e)

    def set_values(self):
        res = super(inheritResConfigSettings, self).set_values()
        # ICPSudo = self.env['ir.config_parameter'].sudo()
        self.set_configs('bare_admin_user', self.bare_admin_user or 'admin')
        self.set_configs('bare_admin_pass', self.bare_admin_pass or 'admin')
        self.set_configs('odoorc_path', self.odoorc_path or 'odoorc_bare')
        self.set_configs('odoorc_port', self.odoorc_port or '9050')
        self.set_configs('bare_tenant_ip', self.bare_tenant_ip or '127.0.0.1')
        self.set_configs('bare_old_admin_pass', self.bare_old_admin_pass or "admin")

        return res
