# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo import SUPERUSER_ID as ADMINUSER_ID
from odoo.exceptions import AccessError,UserError
import odoo

# from odoo.tools import ustr
# from odoo.tools.translate import _
# from odoo import exceptions
# from lxml import etree


class res_config_settings(models.TransientModel):
    _inherit = 'res.config.settings'

    def execute(self):
        self.ensure_one()
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can change the settings"))

        self = self.with_context(active_test=False)
        classified = self._get_classified_fields()

        self.set_values()

        # module fields: install/uninstall the selected modules
        to_install = []
        to_uninstall_modules = self.env['ir.module.module']
        lm = len('module_')
        for name, module in classified['module']:
            if int(self[name]):
                to_install.append((name[lm:], module))
            else:
                if module and module.state in ('installed', 'to upgrade'):
                    to_uninstall_modules += module

        if to_install or to_uninstall_modules:
            self.flush()

        if to_uninstall_modules:
            to_uninstall_modules.with_context({'from_apply': True}).button_immediate_uninstall()

        self._install_modules(to_install)


        if to_install or to_uninstall_modules:
            self.env.reset()
            self = self.env()[self._name]

        config = self.env['res.config'].next() or {}
        if config.get('type') not in ('ir.actions.act_window_close',):
            return config

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }


class module_module(models.Model):
    _inherit = 'ir.module.module'
    
    def button_immediate_install(self):
        conText = self._context
        # print('\n\n Category : ', self.category_id)
        category = self.env['ir.module.category'].search([('id', '=', self.category_id.id)])
        # print('\n\n Context : ', category.name)
        if self._uid != 2 and 'from_apply' not in conText:
            if category.name != 'Account Charts':
                raise AccessError(_("Only Administrator/SuperUser can perform this activity"))

        return super(module_module, self).button_immediate_install()

    def button_uninstall(self):
        conText = self._context
        uid = conText.get('uid')
        category = self.env['ir.module.category'].search([('id', '=', self.category_id.id)])

        if uid != 2 and 'from_apply' not in conText:
            if category.name != 'Account Charts':
                raise AccessError(_("Only administrators can change the settings"))

        if 'from_apply' in conText:
            return super(module_module, self).button_uninstall( )

        if uid != 2 and category.name != 'Account Charts':
            raise UserError(_('Invalid Access'),
                                         _('You are not authorised to uninstall the module...!!! '))
        return super(module_module, self).button_uninstall( )
    
module_module()


class db_name(models.Model):
    _name = 'db.name'
    _description = 'Db name'
    
    name = fields.Char('admin db', size=100)


class db_expire(models.Model):
    _name = "db.expire"
    _description = 'Db Expire'

    db_expire = fields.Boolean('DB expired')

    def create(self, vals):
        exist = self.search([])
        if exist:
            raise AccessError("Not allowed to create multiple records of this kind")
        else:
            return super(db_expire, self).create(vals)

    def write(self, vals):
        if self._uid not in [1, 2, 3, 4, 5]:
            raise AccessError("Update not allowed")
        else:
            return super(db_expire, self).write(vals)
