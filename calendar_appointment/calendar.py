import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class calendar_appointment(models.Model):
    _name = 'calendar.appointment'
    _order = 'name'
    _description = 'Scheduled Appointments'
    
    name = fields.Char(string="Name")
	
class calendar_appointment_spot(models.Model):
    _name = 'calender.appointment.spot'

    name = fields.Char(string="Name")

