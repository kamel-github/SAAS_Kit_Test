from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    web_configuration = fields.Selection([('apache', 'Apache'), ('nginx', 'NGINX')],default='apache',
                                         config_parameter="web_configuration")
