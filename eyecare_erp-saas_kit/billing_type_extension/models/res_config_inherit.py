from odoo import fields, models, api


class ResConfigInherit(models.TransientModel):
    _inherit = 'res.config.settings'
    # _inherits = {'res.config.settings': 'billing'}

    billing = fields.Selection(selection_add=[
                                ('user_plan_price', 'Users + Plan Price')
                                ], string="Billing Type", default="normal")
    plan_users = fields.Integer(readonly=False, string="Default Plan Users", default=3)

    @api.model
    def default_get(self, fields_list):

        print('default get Values. resssss=========', self.plan_users)
        res = super(ResConfigInherit, self).default_get(fields_list)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        values = {
            'plan_users': int(ICPSudo.search([('key', '=', 'plan_users')]).value),
        }

        res.update(values)

        return res

    def get_values(self):
        res = super(ResConfigInherit, self).get_values()
        print ("get values, resssss=======",res)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(
            plan_users= int(ICPSudo.get_param('plan_users')),
        )
        return res

    def set_values(self):
        print('set Values. resssss=========', self.plan_users)
        res = super(ResConfigInherit, self).set_values()
        self.set_configs('plan_users', self.plan_users or 0)
        return res


