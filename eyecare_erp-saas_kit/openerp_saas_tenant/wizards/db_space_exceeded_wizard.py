from odoo import api, models, fields


class DbSpaceExceededWizard(models.TransientModel):
    _name = 'db.space.exceeded'
    _description = 'Database space Exceeded'

    message = fields.Text(readonly=True, default="Database Size Exceeded")