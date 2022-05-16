from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    """ Inherited for adding the user product field in saas setting"""

    user_product = fields.Many2one('product.product', string='User Product',
                                   help="Set the path of Custom modules on Odoo server",
                                   config_parameter="user_product")

    hide_topup = fields.Boolean(string='Hide Top Up Option',help="If set True, it will hide the option of 'Top-up' on the saasmaster website",
                                   config_parameter="hide_topup")
