from odoo import api, models, fields


class MailMAilINherit(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def create(self, values):
        res = super(MailMAilINherit, self).create(values)
        return res
