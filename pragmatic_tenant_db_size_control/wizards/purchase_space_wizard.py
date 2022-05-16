from odoo import api, models, fields


class PurchaseSpace(models.Model):
    _name = 'purchase.additional.space'
    _description = 'Purchase Additional space for user'

    tenant_id = fields.Many2one('tenant.database.list', readonly=True, string='Tenant Database')
    additional_db_size = fields.Float(string='Additional Database Size (GB)')
    additional_filestore_size = fields.Float(string='Additional File Store Size (GB)')

    @api.model
    def default_get(self, fields_list):
        active_id = self._context.get('active_ids')
        tenant_id = self.env['tenant.database.list'].search([('id', '=', active_id)])
        res = super(PurchaseSpace, self).default_get(fields_list)
        res.update({'tenant_id': tenant_id})
        return res

    @api.model
    def create(self, vals_list):
        res = super(PurchaseSpace, self).create(vals_list)
        return res