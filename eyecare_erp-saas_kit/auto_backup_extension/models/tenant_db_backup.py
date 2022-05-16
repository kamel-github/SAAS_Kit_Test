import datetime
import tempfile
import time
from contextlib import closing

import psycopg2

import odoo
from odoo import models, fields, api, tools, _
from odoo.exceptions import Warning, AccessDenied, UserError, AccessError
import paramiko

from odoo import fields, api, models
import os
import logging

_logger = logging.getLogger(__name__)


class TenantBackup(models.Model):
    _inherit = 'db.backup'

    postgres_user = fields.Char(string='Postgres User', required=True, default="postgres")
    postgres_pwd = fields.Char(string='Postgres Password', required=True, default="postgres")
    postgres_port = fields.Char(string="Postgres Default Port", readonly=True, default="5432")

    # tenant_db_name = fields.Many2many('tenant.database.list', string='Tenant Database Names',
    #                                   help='Database you want to schedule backups for', )
    #
    def default_get(self, fields_list):
        res = super(TenantBackup, self).default_get(fields_list)
        res.update({'postgres_user': 'postgres', 'postgres_pwd': 'postgres'})
        return res

    def psycopg2_connection(self):
        rec = self.search([])  # Get Saasmaster_v13 Db name
        if rec.postgres_pwd and rec.postgres_user and rec.host:
            try:
                conn = psycopg2.connect(database='saasmaster_v13',
                                        user=rec.postgres_user,
                                        password=rec.postgres_pwd,
                                        host=rec.host,
                                        port=rec.postgres_port)
                return conn
            except Exception as e:
                _logger.exception(e)
                raise UserError('Unable to Connect Postgres.\nPlease Check Postgres Credentials...!')
        else:
            raise UserError(_('Please Enter Postgres Credentials...!'))

    def check_owner_of_db(self, conn, db_name):
        try:
            with closing(conn.cursor()) as cur:

                cmd = "SELECT d.datname as saasmaster_v13,pg_catalog.pg_get_userbyid(d.datdba) as Owner FROM pg_catalog.pg_database d;"

                cur.execute(cmd)
                rows = cur.fetchall()
            # Variables declaration
            owndbs = []
            owner = None
            # db = self.env['db.backup'].search([])  # Get Saasmaster_v13 Db name
            for row in rows:  # Getting Saasmaster_v13 owner
                if row[0] == db_name:
                    owner = row[1]

            for row in rows:  # Get all dbs of Saasmaster_v13 db owner
                if owner == row[1]:
                    owndbs.append(row[0])

            return {'owner': owner, 'owndbs': owndbs}
        except Exception as e:
            _logger.exception(e)
            raise Exception(e)

    @api.model
    def schedule_backup(self):
        try:
            conn = self.psycopg2_connection()  # Get Connection object of Postgres
            if conn:
                conf_ids = self.search([])
                for rec in conf_ids:
                    try:
                        if not os.path.isdir(rec.folder):
                            os.makedirs(rec.folder)
                    except Exception as e:
                        raise AccessError(_('Error : %s', e))
                    # Create name for dumpfile.
                    try:
                        saas_owner = self.check_owner_of_db(conn, rec.name)  # get owner of saasmaster_v13
                        _logger.info('\n\n\nStarted to Dump All Databases ...............................\n\n\n')
                        for db in saas_owner['owndbs']:
                            self.zip_convert_database(db, rec)
                        conn.close()  # Closed connection of psycopg2 with database
                        _logger.info('\n\n\nStopped Dumping of All Databases and Closed Connection to postgres '
                                     '...............................\n\n\n')



                    except Exception as e:
                        _logger.exception(e)
                        raise UserError(_('Something went Wrong...'))
            else:
                raise UserError(_('Postgres Connection Unsuccess...!'))
        except Exception as e:
            _logger.error('\n\nError : {}'.format(e))

    def zip_convert_database(self, tenanat_db, rec):

        write_path1 = os.path.join(rec.folder, tenanat_db)
        if not os.path.isdir(write_path1):  # Create one folder of db name if not exist
            os.makedirs(write_path1)

        _logger.info('Started to Dump DB...............................{}'.format(tenanat_db))
        bkp_file = '%s_%s.%s' % (time.strftime('%Y_%m_%d_%H_%M_%S'), tenanat_db, rec.backup_type)
        # file_path = os.path.join(rec.folder, bkp_file)
        file_path = os.path.join(write_path1, bkp_file)
        # fp = open(file_path, 'wb')
        try:
            # try to backup database and write it away
            fp = open(file_path, 'wb')
            self._take_dump(tenanat_db, fp, 'db.backup', rec.backup_type)
            fp.close()
        except Exception as error:
            _logger.debug(
                "Couldn't backup database %s. Bad database administrator password for server running at "
                "http://%s:%s" % (tenanat_db, rec.host, rec.port))
            _logger.debug("Exact error from the exception: %s", str(error))

        # Check if user wants to write to SFTP or not.
        if rec.sftp_write is True:
            try:
                # Store all values in variables
                dir = rec.folder
                # path_to_write_to = rec.sftp_path

                path_to_write_to = os.path.join(rec.sftp_path, tenanat_db)
                if not os.path.isdir(path_to_write_to):  # Create one folder of db name if not exist for sftp
                    os.makedirs(path_to_write_to)

                ip_host = rec.sftp_host
                port_host = rec.sftp_port
                username_login = rec.sftp_user
                password_login = rec.sftp_password
                _logger.debug('sftp remote path: %s', path_to_write_to)

                try:
                    s = paramiko.SSHClient()
                    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    s.connect(ip_host, port_host, username_login, password_login, timeout=20)
                    sftp = s.open_sftp()
                except Exception as error:
                    _logger.critical('Error connecting to remote server! Error: %s', str(error))

                try:
                    sftp.chdir(path_to_write_to)
                except IOError:
                    # Create directory and subdirs if they do not exist.
                    current_directory = ''
                    for dirElement in path_to_write_to.split('/'):
                        current_directory += dirElement + '/'
                        try:
                            sftp.chdir(current_directory)
                        except:
                            _logger.info('(Part of the) path didn\'t exist. Creating it now at %s',
                                         current_directory)
                            # Make directory and then navigate into it
                            sftp.mkdir(current_directory, 777)
                            sftp.chdir(current_directory)
                            pass
                sftp.chdir(path_to_write_to)
                # Loop over all files in the directory.
                for folder in os.listdir(dir):
                    filefolder = os.path.join(dir, folder)
                    for f in os.listdir(filefolder):
                        if tenanat_db in f:
                            fullpath = os.path.join(filefolder, f)
                            if os.path.isfile(fullpath):
                                try:
                                    sftp.stat(os.path.join(path_to_write_to, f))
                                    _logger.debug(
                                        'File %s already exists on the remote FTP Server ------ skipped', fullpath)
                                # This means the file does not exist (remote) yet!
                                except IOError:
                                    try:
                                        sftp.put(fullpath, os.path.join(path_to_write_to, f))
                                        _logger.info('Copying File % s------ success', fullpath)
                                    except Exception as err:
                                        _logger.critical(
                                            'We couldn\'t write the file to the remote server. Error: %s', str(err))

                # Navigate in to the correct folder.
                sftp.chdir(path_to_write_to)

                _logger.debug("Checking expired files")
                # Loop over all files in the directory from the back-ups.
                # We will check the creation date of every back-up.
                for file in sftp.listdir(path_to_write_to):
                    if tenanat_db in file:
                        # Get the full path
                        fullpath = os.path.join(path_to_write_to, file)
                        # Get the timestamp from the file on the external server
                        timestamp = sftp.stat(fullpath).st_mtime
                        createtime = datetime.datetime.fromtimestamp(timestamp)
                        now = datetime.datetime.now()
                        delta = now - createtime
                        # If the file is older than the days_to_keep_sftp (the days to keep that the user filled in
                        # on the Odoo form it will be removed.
                        if delta.days >= rec.days_to_keep_sftp:
                            # Only delete files, no directories!
                            if ".dump" in file or '.zip' in file:
                                _logger.info("Delete too old file from SFTP servers: %s", file)
                                sftp.unlink(file)
                # Close the SFTP session.
                sftp.close()
                s.close()
            except Exception as e:
                try:
                    sftp.close()
                    s.close()
                except:
                    pass
                _logger.error('Exception! We couldn\'t back up to the FTP server. Here is what we got back '
                              'instead: %s', str(e))
                # At this point the SFTP backup failed. We will now check if the user wants
                # an e-mail notification about this.
                if rec.send_mail_sftp_fail:
                    try:
                        ir_mail_server = self.env['ir.mail_server'].search([], order='sequence asc', limit=1)
                        message = "Dear,\n\nThe backup for the server " + rec.host + " (IP: " + rec.sftp_host + \
                                  ") failed. Please check the following details:\n\nIP address SFTP server: " + \
                                  rec.sftp_host + "\nUsername: " + rec.sftp_user + \
                                  "\n\nError details: " + tools.ustr(e) + \
                                  "\n\nWith kind regards"
                        catch_all_domain = self.env["ir.config_parameter"].sudo().get_param(
                            "mail.catchall.domain")
                        response_mail = "auto_backup@%s" % catch_all_domain if catch_all_domain else self.env.user.partner_id.email
                        msg = ir_mail_server.build_email(response_mail, [rec.email_to_notify],
                                                         "Backup from " + rec.host + "(" + rec.sftp_host +
                                                         ") failed",
                                                         message)
                        ir_mail_server.send_email(msg)
                    except Exception as e:
                        pass
        """
            Remove all old files (on local server) in case this is configured..
        """
        if rec.autoremove:
            directory = rec.folder
            # Loop over all files in the directory.
            for f in os.listdir(directory):
                fullpath = os.path.join(directory, f)  # /db_name
                # Only delete the ones wich are from the current database
                # (Makes it possible to save different databases in the same folder)
                if tenanat_db in fullpath:
                    for file in os.listdir(fullpath):
                        filepath = os.path.join(fullpath, file)
                        timestamp = os.stat(filepath).st_ctime
                        createtime = datetime.datetime.fromtimestamp(timestamp)
                        now = datetime.datetime.now()
                        delta = now - createtime
                        #       '_____________________________________files pass')
                        # pass
                        if delta.days >= rec.days_to_keep:
                            # Only delete files (which are .dump and .zip), no directories.
                            if os.path.isfile(filepath) and (".dump" in file or '.zip' in file):
                                _logger.info("Delete local out-of-date file: %s", filepath)
                                os.remove(filepath)
