from odoo import models, fields
from odoo.http import request


class TenantDatabaseList(models.Model):
    _inherit = "tenant.database.list"

    tenant_db_url = fields.Char(compute='get_tenant_db_url', string='Tenant db URL')

    def get_tenant_db_url(self):
        for o in self:
            ICPSudo = request.env['ir.config_parameter'].sudo()
            brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
            if 'http://' in brand_website:
                url = 'http://'
            elif 'https://' in brand_website:
                url = 'https://'
            o.tenant_db_url = "%s%s" % (url, o.tenant_url)

