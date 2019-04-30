from odoo import api, fields, models
from odoo import tools
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class Meeting(models.Model):
    """ Model for Calendar Event

        Special context keys :
            - `no_mail_to_attendees` : disabled sending email to attendees when creating/editing a meeting
    """

    _inherit = 'calendar.event'
