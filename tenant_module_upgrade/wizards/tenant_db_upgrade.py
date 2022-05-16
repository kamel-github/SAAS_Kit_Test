from odoo import fields, api, models, _
from odoo import SUPERUSER_ID, api
from odoo import sql_db, _
from contextlib import closing


class TenantDbUpgrade(models.TransientModel):
    _name = 'tenant.db.upgrade'
    _description = 'Tenant Database Upgrade'

    tenant_db = fields.Many2many('tenant.database.list', string='Tenant DB')
    installed_modules = fields.One2many("installed.tenant.module", 'tenant_module_id',
                                        string="Installed Modules")
    db_list = []

    def upgrade(self):
        for db in self.tenant_db:
            database_name = db.name
            for mod in self.installed_modules:
                if mod.upgrade_bool:
                    db = sql_db.db_connect(database_name)
                    with closing(db.cursor()) as cr:
                        env = api.Environment(cr, SUPERUSER_ID, {})
                        module_name = env['ir.module.module'].search(
                            [('name', '=', mod.technical_name), ('state', '=', 'installed')])
                        module_name.button_immediate_upgrade()

    def load_modules(self):
        module_list_1 = []
        module_list_2 = []
        for db in self.tenant_db:
            db_name = db.name
            db = sql_db.db_connect(db_name)
            with closing(db.cursor()) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                installed_apps = env['ir.module.module'].search(
                    [('state', '=', 'installed')]) #, ('application', '=', True)
                id = self.id
                for module in installed_apps:
                    module_list_1.append((0, 0, {'tenant_module_id': id,
                                                 'module_name': module.shortdesc,
                                                 'technical_name': module.name,
                                                 'status': module.state
                                                 }))
        for module in module_list_1:
            if module not in module_list_2:
                module_list_2.append(module)
        self.write({'installed_modules': module_list_2})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tenant.db.upgrade',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }


class InstalledTenantModules(models.TransientModel):
    _name = 'installed.tenant.module'
    _description = 'Tenant Database Installed Modules'

    tenant_module_id = fields.Many2one('tenant.db.upgrade', string="module Id")
    upgrade_bool = fields.Boolean(default=False, string="Check", store=True)
    module_name = fields.Char('Module Name')
    technical_name = fields.Char('Module Technical Name')
    status = fields.Selection([('installed', 'Installed'),
                               ('uninstalled', 'Uninstalled'),
                               ('uninstallable', 'Uninstallable'),
                               ('to upgrade', 'To be Upgrade'),
                               ('to remove', 'To be Remove'),
                               ('to install', 'To be Install')])
