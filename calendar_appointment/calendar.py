import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging


_logger = logging.getLogger(__name__)


class calendar_appointment(models.Model):
	
	_name = 'calendar.appointment' # Kan förekommer i dropdown t ex
	_description = 'Appointments for calendar'

	name = fields.Char(string = 'Name')
	attendee_ids = fields.Many2many(comodel_name ='res.partner') # Comodel_name 
	# ~ product_ids = fields.Many2many(comodel_name = 'product.product')
	spot_ids = fields.One2many(comodel_name = 'calendar.appointment.spot', inverse_name = 'appointment_id')
	user_id = fields.Many2one(comodel_name = 'res.user')
	is_published = fields.Boolean(string = 'Publish') # String represents a label
	description = fields.Text(string = 'Descriptions')
	meeting_type = fields.Selection([('One2one', 'One to One'),('Many2one', 'Many to One'),], 'Type Selections') # Ena värdet visa i dropdown och andra lagras i DB:n
	date_due = fields.Date(string = 'Dates')

	
class calendar_appointment_spot(models.Model):

    _name = 'calendar.appointment.spot'
    _description = 'Spot for calendars appointment'
    
    
    name = fields.Char(string='Name')
    appointment_id = fields.Many2one(comodel_name='calendar.appointment')
    partner_ids = fields.Many2many(comodel_name='res.partner')
    calendar_id = fields.Many2one(comodel_name='calendar.event')
    note = fields.Text(string='Note field')
    date_start = fields.Datetime(string = 'Date start')
    duration = fields.Float(string = 'Duration')
	# ~ date_end = 
	
class calendar_event(models.Model):
	
	_inherit = 'calendar.event'
	
	
	appointment_id = fields.Many2one(comodel_name='calendar.appointment')
	
	
class Wizard(models.TransientModel):
	_name = 'calendar.wizard'
	_description = 'Wizard for adding spots'
	
	def _default_session(self):
		return self.env['calendar.session'].browse(self._context.get('active_id'))
	
	session_id = fields.Many2one('calendar.session', string='Session', required=True)
	attendee_ids = fields.Many2many('res.partner', string='Attendees')
