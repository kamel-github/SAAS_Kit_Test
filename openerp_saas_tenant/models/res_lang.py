from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class resLang(models.Model):
    _inherit = "res.lang"

    def install_language(self):

        _logger.info('\n\nInvoking install language wizard')
        action_install = self.env.ref('base.action_view_base_language_install')
        _logger.info('\n\naction install object : {} {}'.format(action_install.res_model,action_install.res_id,))

        self.active = True

        lang_id = self.env[action_install.res_model].create({
            'lang':self.code,
            'overwrite':True
        })

        _logger.info('\n\n install id1 : {} {}'.format(action_install.res_model, lang_id))
        ret = lang_id.lang_install()

        lang_id2 = self.env[action_install.res_model].search([('id', '=', int(ret['res_id']))])
        _logger.info('\n\nLanguage added : {} {}'.format(action_install.res_model, lang_id2))
        # if lang_id2:
        #     ret = lang_id2.switch_lang()
        #     _logger.info('\n\n language switched : {} {}'.format(action_install.res_model, ret,))

        return True