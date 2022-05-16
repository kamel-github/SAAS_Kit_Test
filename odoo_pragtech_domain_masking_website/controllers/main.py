from odoo import http
from odoo.http import request
import base64
from odoo.exceptions import UserError


class ShowDb(http.Controller):
    @http.route('/domain/datas', methods=['POST'], auth='public', type='http', website=True, csrf=False)
    def show_dbs(self, **kw):
        domain = kw['client_domain']
        type = kw.get('domain')
        db = kw.get('db_name')
        db_id = request.env['tenant.database.list'].sudo().search([('name', '=', db)])
        values = {'client_domain': domain,
                  'client_ssl1_filename': kw.get('domain_key').filename,
                  'client_ssl2_filename': kw.get('domain_crt').filename,
                  'client_ssl3_filename': kw.get('domain_chain_crt').filename,
                  'domain_type': type,
                  'tenant_db_management': db_id.id,
                  'client_ssl3': base64.encodebytes((kw.get('domain_chain_crt')).read()),
                  'client_ssl2': base64.encodebytes((kw.get('domain_crt')).read()),
                  'client_ssl1': base64.encodebytes((kw.get('domain_key')).read()),
                  }
        domain_masking_obj_id = request.env['domain.masking.details'].sudo().create(values)
        obj_id = int(domain_masking_obj_id.id)
        domain_masking_obj_brows = request.env['domain.masking.details'].sudo().browse(obj_id)

        if domain_masking_obj_id:
            domain_masking_obj_brows.action_set_client_domain()
            domain_masking_obj_brows.tenant_db_management.action_restart_apache()
        else:
            raise UserError("Try again")
