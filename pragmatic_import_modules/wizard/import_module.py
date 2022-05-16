import subprocess
from odoo import models, fields, exceptions, _, api
from odoo.exceptions import UserError, ValidationError
from zipfile import ZipFile
import os
import os.path
from os import path
import base64
import signal
from subprocess import Popen, PIPE
import threading
import logging

_logger = logging.getLogger(__name__)


class ImportModule(models.TransientModel):
    _name = 'import.module'
    _description = "Import Custom Addons"

    filename = fields.Char(string="Filename")
    file = fields.Binary('Upload File')

    @api.model
    def action_restart_server(self):
        # config_path = self.env['ir.config_parameter'].sudo()
        # saas_rc = config_path.search([('key', '=', 'saasmaster_rc_path')]).value
        # if saas_rc:
        # command = "sudo"+" "+saas_rc+" "+"force-reload"
        os.system("sudo /etc/init.d/odoosaas-server restart")
        # else:
        # raise UserError(_("Please gave Saasmaster RC file path"))

    @api.model
    def action_restart_bare_server(self):
        # config_path = self.env['ir.config_parameter'].sudo()
        # bare_rc = config_path.search([('key', '=', 'bare_rc_path')]).value
        # if bare_rc:
        #     command = "sudo" + " " + bare_rc + " " + "force-reload"
        os.system("sudo /etc/init.d/odoosaas-bare restart")
        # else:
        #     raise UserError(_("Please gave Bare RC file path"))


    # def restart_server(self):
    #     port = 8085
    #     process = Popen(["lsof", "-i", ":{0}".format(port)], stdout=PIPE, stderr=PIPE)
    #     stdout, stderr = process.communicate()
    #     for process in str(stdout.decode("utf-8")).split("\n")[1:]:
    #         data = [x for x in process.split(" ") if x != '']
    #         if len(data) <= 1:
    #             continue
    #         if data[1]:
    #             os.kill(int(data[1]), signal.SIGKILL)
    #
    #     cmd = './odoo-bin -c .odoorc_bare --xmlrpc-port {} -d saasmaster_v14 --no-http --stop-after-init'.format(port)
    #     subprocess.call(cmd, shell=True)
    # os.system('./odoo-bin -c .odoorc_tenant --db-filter=saasmaster_v14 --without-demo=all --stop-after-init') #
    # --db-filter=saasmaster_v14 --without-demo=all --stop-after-init
    def import_module(self):
        _logger.info(_('\n------------------ STARTED IMPORT MODULE------------------\n'))
        config_path = self.env['ir.config_parameter'].sudo()
        custom_addons_path = config_path.search(
            [('key', '=', 'custom_addons_path')]).value  # get value from saas settings(user given path)
        _logger.info(_('\n\nADDONS PATH FOR IMPORT MODUELS : %s' % custom_addons_path))
        if self.filename:
            if custom_addons_path:
                path = custom_addons_path + self.filename
            else:
                raise exceptions.UserError(_("Please define custom addons path in SaaS config!"))
        else:
            raise exceptions.UserError(_("Select zip file!"))

        if self.filename.endswith('.zip'):
            _logger.info(_('\n\nZIP FIILE TO EXRACT 1 : File name: %s \n Path : %s' % (self.filename, path)))
            try:
                files = ''
                with open(path, 'wb') as file:
                    extracted_filename = '-'.join(self.filename.split('-')[:-1])
                    _logger.info(_('\n\n FOLDER/FILE NAME 2 : %s \n' % extracted_filename))
                    if os.path.isdir(custom_addons_path + extracted_filename):
                        _logger.info(_('\n\nPATH AVAILABLE  3 : %s%s \n' % (custom_addons_path, extracted_filename)))
                        return {
                            'name': 'Are you sure?',
                            'type': 'ir.actions.act_window',
                            'res_model': 'message.wizard',
                            'view_mode': 'form',
                            'view_type': 'form',
                            'target': 'new',
                            'context': {
                                'wiz_id': self.id,
                            },
                        }
                    else:
                        files = file.write(base64.b64decode(self.file))
                if files:
                    with ZipFile(custom_addons_path + self.filename, 'r') as zip_ref:
                        _logger.info(_('\n\n ZIP FIILE TO EXRACT 4 : %s \n' % zip_ref))
                        zip_ref.extractall(custom_addons_path)
                        os.remove(path)
                        _logger.info(_('\n\n DONE EXTRACTION OF FILE AND REMOVED ZIP FILE : %s \n' % path))
                        # self.restart_server()
                        self.env['ir.module.module'].update_list()  # for update the apps list
                        # os.system("sudo /etc/init.d/odoosaas force-reload")

            except Exception as e:
                print(e)
                raise exceptions.UserError(_("Something went wrong. Please Try again !"))
        else:
            raise exceptions.UserError(_("Please upload zip file !"))


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    _description = "Message Wizard"

    message = fields.Char(default='Folder is already there,Do you want to replace it..?')

    def yes_confirmed(self):
        config_path = self.env['ir.config_parameter'].sudo()
        custom_addons_path = config_path.search(
            [('key', '=', 'custom_addons_path')]).value
        id = self._context.get('wiz_id')
        wiz_id = self.env['import.module'].sudo().search([('id', '=', id)])
        path = custom_addons_path + wiz_id.filename

        _logger.info(_('\n\nZIP FIILE TO EXRACT 5 : %s \n' % path))
        with open(path, 'wb') as file:
            file.write(base64.b64decode(wiz_id.file))
        with ZipFile(custom_addons_path + wiz_id.filename, 'r') as zip_ref:
            _logger.info(_('\n\n STARTED ZIP FILE FOR EXTRACTION : %s \n' % path))
            zip_ref.extractall(custom_addons_path)
            os.remove(path)
            _logger.info(_('\n\n DONE EXTRACTION OF ZIP FILE : %s \n' % path))
            self.env['ir.module.module'].update_list()
            # os.system('sudo /etc/init.d/odoosaas force-reload')

    def not_confirmed(self):
        pass


class UpdateRcPath(models.TransientModel):
    _name = "update.rc.path"
    _description = "Update RC Path for New Applications"

    new_addons_path = fields.Text(string="New Addons Path", copy=False)
    rc_type = fields.Selection([('bare', 'Bare RC File'),
                                ('saas', 'Saas RC File')], string=' RC Type', default="bare")

    @api.onchange('rc_type')
    def _onchange_get_rc_data(self):
        # print("\n\n\nn\nself.rc_type", self.rc_type," \n\n\nn\n")
        conf = self.env['ir.config_parameter']
        file = None
        if not path.exists(conf.get_param('saasmaster_rc_path')):
            raise UserError(_('File/Path does not exists....!'))

        if not path.exists(conf.get_param('odoorc_path')):
            raise UserError('File/Path does not exists....!')

        if self.rc_type == 'saas':
            file = open(conf.get_param('saasmaster_rc_path'), "r")
        elif self.rc_type == 'bare':
            file = open(conf.get_param('odoorc_path'), "r")

        if file:
            line = file.readlines()
            for i in range(len(line)):
                if "addons_path" in line[i]:
                    self.new_addons_path = line[1]
        file.close()

    def set_rc_data(self):
        f = None
        conf = self.env['ir.config_parameter']

        if self.rc_type == 'saas':
            f = open(conf.get_param('saasmaster_rc_path'), "r")
        elif self.rc_type == 'bare':
            f = open(conf.get_param('odoorc_path'), "r")

        line = f.readlines()
        f.close()

        for i in range(len(line)):
            if "addons_path" in line[i]:
                line[i] = self.new_addons_path + "\n"

        f2 = None
        if self.rc_type == 'saas':
            f2 = open(conf.get_param('saasmaster_rc_path'), "w")
        elif self.rc_type == 'bare':
            f2 = open(conf.get_param('odoorc_path'), "w")
        f2.writelines(line)
        f2.close()

        if self.rc_type == 'saas':
            os.system("sudo /etc/init.d/odoosaas force-reload")
        elif self.rc_type == 'bare':
            os.system('sudo /etc/init.d/odoosaas-bare-server reload')
