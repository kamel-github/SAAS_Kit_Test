from . import controller
from . import models
from odoo.http import request
from odoo.models import BaseModel
from odoo import SUPERUSER_ID, api
from odoo import sql_db, _
from odoo.exceptions import ValidationError
from contextlib import closing

# monkey patch
def unarchive_users():
    """
    for restrict the tenant db user to unarchive
    """

    def action_unarchive(self):
        if self._name == 'res.users':
            db_name = self.env.cr.dbname
            db = sql_db.db_connect(db_name)
            with closing(db.cursor()) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                Task = env['saas.service']
                db = Task.search([('name', '=', db_name)])
                if db.user_count <= db.use_user_count:
                    raise ValidationError(_('Sorry You cant Unarchive'))
                else:
                    return self.filtered(lambda record: not record[self._active_name]).toggle_active()
        else:
            return self.filtered(lambda record: not record[self._active_name]).toggle_active()

    BaseModel.action_unarchive = action_unarchive
