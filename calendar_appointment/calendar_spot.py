import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

	
class calendar_appointment_spot(models.Model):

	_name = 'calendar.appointment.spot'
	_description = 'Spot for calendars appointment'
	
	
	name = fields.Char(string='Name')
	# ~ appointment_id = fields.Many2one(comodel_name='calendar.appointment')
	partner_ids = fields.Many2many(comodel_name='res.partner')
	calendar_id = fields.Many2one(comodel_name='calendar.event')
	note = fields.Text(string='Note field')
