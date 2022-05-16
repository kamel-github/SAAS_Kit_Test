from odoo import models, fields, api
import json
import re


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    custom_addons_path = fields.Char(string='Custom Module Path', size=200,
                                     help="Set the path of Custom modules on Odoo server",
                                     config_parameter="custom_addons_path")
    saasmaster_rc_path = fields.Char(string='Saasmaster RC Path', config_parameter="saasmaster_rc_path")
