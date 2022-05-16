from odoo import models,fields, api
# from .hooks import uninstall_hook, post_load
from odoo.api import Environment, SUPERUSER_ID

#
# def uninstall_hook(cr, registry):
#     """ Uninstall Hook Function """
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     ICPSudo = env['ir.config_parameter'].sudo()
#     ICPSudo.set_param('tenant_filestore_size', "0")
#     ICPSudo.set_param('tenant_db_size', "0")
#     print('\n\n\nUninstall Hook\n\n\n')


class sale_order(models.Model):
    _inherit = 'sale.order'
    #
    # db_space = fields.Boolean('DB space', readonly=True, default=False)
    # filestore_space = fields.Boolean('Filestore space', readonly=True, default=False)

    def post_installation_work(self):
        res = super(sale_order, self).post_installation_work()
        if self.saas_order:
            db_name = str(self.instance_name).lower().replace(" ", "_")
            tenant_database_list_obj = self.env['tenant.database.list'].sudo().search([('name', '=', db_name)])
            ICPSudo = self.env['ir.config_parameter'].sudo()
            tenant_db_size = ICPSudo.search([('key', '=', 'tenant_db_size')]).value
            tenant_filestore_size = ICPSudo.search([('key', '=', 'tenant_filestore_size')]).value
            tenant_database_list_obj.tenant_db_size = float(tenant_db_size)
            tenant_database_list_obj.tenant_filestore_size = float(tenant_filestore_size)
        return res
