import odoo
from odoo import SUPERUSER_ID
from odoo import models, fields, api
from odoo.tools import config


class saas_config_setting(models.TransientModel):
    _inherit = 'res.config.settings'

    apache_ssl_path = fields.Char(size=200,
                                  help="Path to store Apache Certificates of client domain",
                                  config_parameter="apache_ssl_path",
                                  string="Apache/NGINX SSL Certificate Directory")
    apache_config_file = fields.Char(size=200,
                                     help="Apache2 Virtual Configuration file path",
                                     config_parameter="apache_config_file", string="Apache/NGINX Config. File Path")

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(saas_config_setting, self).default_get(fields_list)
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     values = {
    #         'apache_ssl_path' : ICPSudo.search([('key', '=', 'apache_ssl_path')]).value,
    #         'apache_config_file' : ICPSudo.search([('key', '=', 'apache_config_file')]).value,
    #     }
    #
    #     res.update(values)
    #
    #     return res
    #
    #
    #
    # def get_values(self):
    #     res = super(saas_config_setting, self).get_values()
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     res.update(
    #         apache_ssl_path = ICPSudo.get_param('apache_ssl_path'),
    #         apache_config_file = ICPSudo.get_param('apache_config_file'),
    #     )
    #     return res
    #
    #
    # def set_values(self):
    #     res = super(saas_config_setting, self).set_values()
    #     self.set_configs('apache_ssl_path', self.apache_ssl_path or '/etc/apache2/ssl/')
    #     self.set_configs('apache_config_file', self.apache_config_file or '/etc/test.conf')
    #
    #     return res
