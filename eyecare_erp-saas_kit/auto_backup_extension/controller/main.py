import base64
import io
import zipfile

import odoo
from odoo import http, fields, exceptions, _
from odoo.http import request, content_disposition
from urllib.parse import urlparse

try:
    from addons.website_sale.controllers.main import WebsiteSale
except:
    from odoo.addons.website_sale.controllers.main import WebsiteSale

import os
import datetime
import logging

_logger = logging.getLogger(__name__)

from ... import saas_product


class saas_pro_inherit(saas_product.controller.main.saas_pro):

    @http.route('/download/db_backup', auth='public', website=True)
    def _make_zip(self, **kw):
        """returns zip files for the Document Inspector and the portal.
        :return: a http response to download a zip file.
        """
        path = urlparse(kw['id'])
        name = os.path.basename(path.path)  # File name
        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                with zipfile.ZipFile(kw['id'], 'r') as zip_ref:
                    listoffiles = zip_ref.namelist()
                    for attachment in listoffiles:
                        datas = base64.b64encode(zip_ref.read(attachment))
                        filename = attachment
                        doc_zip.writestr(filename, base64.b64decode(datas),
                                         compress_type=zipfile.ZIP_DEFLATED)
        except zipfile.BadZipfile:
            _logger.exception("BadZipfile exception")
        content = stream.getvalue()
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    @http.route('/apps/db_details', auth='public', website=True)
    def db_details(self, **kw):
        user = False
        if request.session.uid:
            user = request.session.uid
            user = request.env['res.users'].sudo().search([('id', '=', user)])

        tenant = request.env['tenant.database.list'].sudo().search([('id', '=', kw.get('id'))])
        # return json.dumps(tenant.id)
        registry = odoo.registry(tenant.name)
        users = []
        users_inactive = []
        with registry.cursor() as tenant_cr:
            tenant_env = odoo.api.Environment(tenant_cr, 1, {})
            main_tenant_user = tenant_env['res.users'].sudo().search([('tenant_user', '=', True)], limit=1)
            active_domain = []
            inactive_domain = [('active', '=', False)]

            if main_tenant_user:
                active_domain.append(('id', '>=', main_tenant_user.id))
                inactive_domain.append(('id', '>=', main_tenant_user.id))

            tenant_users = tenant_env['res.users'].sudo().search(active_domain)
            for item in tenant_users:
                if item.tenant_user:
                    users.append({'name': item.name, 'login': item.login, 'sub_user': True})
                else:
                    users.append({'name': item.name, 'login': item.login, 'sub_user': False})

            tenant_users = tenant_env['res.users'].sudo().search(inactive_domain)
            for item in tenant_users:
                users_inactive.append({'name': item.name, 'login': item.login, 'sub_user': False})
            AllzipFiles = []
            ###################################################################
            backup_store_path = request.env['db.backup'].sudo().search([])
            if backup_store_path and backup_store_path.folder:
                tenant_path = os.path.join(backup_store_path.folder, tenant.name)
                if os.path.exists(tenant_path):
                    for file in os.listdir(tenant_path):
                        filepath = os.path.join(tenant_path, file)
                        timestamp = os.stat(filepath).st_mtime
                        createtime = datetime.datetime.fromtimestamp(timestamp)
                        dictdata = {'file': file, 'download_path': filepath,
                                    'createdate': createtime}

                        AllzipFiles.append(dictdata)
            ###################################################################
        res = {
            'tenant': tenant,
            'users': users,
            'users_inactive': users_inactive,
            'db': tenant.name,
            'backup_files':False,
        }
        if AllzipFiles:
            files = {'backups': AllzipFiles}
            res.update(files)
            res['backup_files'] = True
        return request.render('saas_product.saas_tenants', res)
