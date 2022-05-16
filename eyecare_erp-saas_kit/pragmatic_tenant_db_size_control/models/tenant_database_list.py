from contextlib import closing
from datetime import datetime, timedelta
import odoo
from odoo.http import request
from odoo import api, models, fields, _, sql_db, SUPERUSER_ID
import os
import xmlrpc
import math

import logging

_logger = logging.getLogger(__name__)


class TenantDatabaseListInherit(models.Model):
    _inherit = "tenant.database.list"

    tenant_db_size = fields.Float(string='Default Tenant DB Size(GB)')
    tenant_filestore_size = fields.Float(string="Default Tenant Filestore Size(GB)")
    total_db_size_used = fields.Float(string='Total DB Size Used (GB)')
    total_filestore_size_used = fields.Float(string='Total FileStore Size Used (GB)')
    volume_history = fields.One2many('tenant.volume.history', 'tenant_id', string="Volume History")
    purchase_space = fields.Boolean(default=False)

    def schedule_volume_backup(self):
        tenant_dbs = self.env['tenant.database.list'].search([])
        ICPSudo = self.env['ir.config_parameter'].sudo()
        mypath = ICPSudo.search([('key', '=', 'filestore_path')]).value
        if mypath[-1] == '/':
            mypath = mypath.rstrip(mypath[-1])
        # mypath = '/home/shital/.local/share/Odoo/filestore'
        dirs = os.listdir(mypath)  # All Filestores saved in odoo

        for dir_name in dirs:
            path = os.path.join(mypath, dir_name)

            if os.path.exists(path):
                for tenant in tenant_dbs:  # Get Tenant Dbs
                    if dir_name == tenant.name:
                        flush_record_before = ICPSudo.search([('key', '=', 'flush_storage_history')]).value
                        if flush_record_before:
                            date_today = datetime.now()
                            date_before = timedelta(days=int(flush_record_before))
                            expiry_date = date_today - date_before
                            expired_records = self.env['tenant.volume.history'].search([('date', '<', expiry_date),
                                                                                        ('tenant_id', '=', tenant.id)])
                            if expired_records:
                                _logger.info('Unlinking Data History________________________________')
                                expired_records.unlink()

                        dir_size = self.get_size(path)
                        filestore_size_in_gb = "{:.2f}".format(((dir_size / 1024) / 1024) / 1024)
                        db_size_val = 0
                        if self.get_db_size(dir_name):
                            db_size = self.get_db_size(dir_name)
                            db_size_val = float(db_size.split(' ')[0])
                            db_size_val = "{:.2f}".format(db_size_val / 1024)

                        vals = {
                            'tenant_id': tenant.id,
                            'tenant_db_size': float(db_size_val),
                            'tenant_filestore_size': float(filestore_size_in_gb),
                            'date': datetime.now(),
                        }

                        volume_id = self.env['tenant.volume.history'].create(vals)
                        tenant.volume_history = [(1, 0, [volume_id])]
                        tenant.total_filestore_size_used = float(filestore_size_in_gb)
                        tenant.total_db_size_used = float(db_size_val)
                        _logger.info('')
                        self.update_saas_service(tenant)

                        if not tenant.purchase_space:
                            if tenant.total_db_size_used >= tenant.tenant_db_size or tenant.total_filestore_size_used >= tenant.tenant_filestore_size:
                                tenant.purchase_space = True

            else:
                _logger.info(_("File Store not exist  '%s'" % path))

    def update_saas_service(self, tenant):
        ICPSudo = request.env['ir.config_parameter'].sudo()
        brand_website = ICPSudo.search([('key', '=', 'brand_website')]).value
        brand_admin = ICPSudo.search([('key', '=', 'admin_login')]).value
        brand_pwd = ICPSudo.search([('key', '=', 'admin_pwd')]).value
        dest_model = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(brand_website))
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(brand_website))
        uid_dst = common.authenticate(tenant.name, brand_admin, brand_pwd, {})

        dest_model.execute_kw(tenant.name, uid_dst, brand_pwd, 'saas.service', 'write',
                              [1,
                               {
                                   'tenant_db_size': tenant.tenant_db_size,
                                   'tenant_filestore_size': tenant.tenant_filestore_size,
                                   'total_db_size_used': tenant.total_db_size_used,
                                   'total_filestore_size_used': tenant.total_filestore_size_used,
                               }]
                              )
        return True

    @api.model
    def get_db_size(self, db_name):
        try:
            db = odoo.sql_db.db_connect('postgres')
            with closing(db.cursor()) as cr:
                query = """ SELECT pg_size_pretty( pg_database_size('{}') );""".format(db_name)
                cr.execute(query)
                all = cr.fetchone()
                # print("\n\n Db name : ", db_name, "\n\nSize : ", all[0])
                return all[0]
        except Exception as e:
            print("Exception : ", e)
            return False

    @api.model
    def get_size(self, start_path='.'):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)

        return total_size


class TenantVolumeHistory(models.Model):
    _name = "tenant.volume.history"
    _description = ''' Get Date Wise History of db and filestore volume'''

    tenant_id = fields.Many2one('tenant.database.list', string='Tenant Database')
    tenant_db_size = fields.Float(string='Database Size (GB)')
    tenant_filestore_size = fields.Float(string='File Store Size (GB)')
    date = fields.Datetime(string="Date")
