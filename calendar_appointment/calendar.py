import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
from datetime import timedelta, time


_logger = logging.getLogger(__name__)


class calendar_appointment(models.Model):
	
	_name = 'calendar.appointment' # Kan förekommer i dropdown t ex
	_description = 'Appointments for calendar'

	name = fields.Char(string = 'Name')
	attendee_ids = fields.Many2many(comodel_name ='res.partner') # Comodel_name 
	# ~ product_ids = fields.Many2many(comodel_name = 'product.product')
	spot_ids = fields.One2many(comodel_name = 'calendar.appointment.spot', inverse_name = 'appointment_id')
	user_id = fields.Many2one(comodel_name = 'res.users')
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
    date_end = fields.Datetime(string = 'Date End')
	
class calendar_event(models.Model):
	
	_inherit = 'calendar.event'
	
	
	appointment_id = fields.Many2one(comodel_name='calendar.appointment')
	
	# ~ På en appointment, lägg till spots. Wizard: Välj antal, längd, när på dagen för första spot och antal spots per dag.
class Wizard(models.TransientModel):
	_name = 'calendar.appointment.wizard'
	_description = 'Wizard for adding spots'
	
	def _default_appointment(self):
		return self.env['calendar.appointment'].browse(self._context.get('active_id'))
	
	date_start = fields.Datetime(string='Start Date')
	date_stop = fields.Datetime(string='Stop Date')
	duration = fields.Float(string='Duration')
	nmbr_spots = fields.Integer(string='Number of Spots')
	nmbr_spots_per_day = fields.Integer(string='Number of spots per day')
	
	@api.multi
	def create_spots(self):
		new_day = 0
		spots_i = 1
		
		spot_ids = []
		while spots_i <= self.nmbr_spots:
			spots_per_day_i = 1
			while spots_per_day_i <= self.nmbr_spots_per_day and spots_i <= self.nmbr_spots:
				
				appointment = self._default_appointment()
				event_list = self.env['calendar.event'].search([('start_date','>=',self.date_start), ('stop_date', '<=',self.date_stop), ('user_id', '=', appointment.user_id.id)])
				# ~ event_list_item = event_list[spots_per_day_i-1]
				
				spot_datetime = self.date_start + timedelta(hours=((spots_per_day_i - 1) * self.duration), days=new_day)
				# ~ _logger.warn(spot_datetime)
				
				if event_list:
					_logger.warn("THIS IS SPARTA")
					
				spot_ids.append(self.env['calendar.appointment.spot'].create({
				'date_start' : spot_datetime,
				'date_end' : self.date_stop,
				'appointment_id' : self._context.get('active_id'),
				'duration' : self.duration}).id)
			
				spots_per_day_i += 1
				spots_i += 1
				
			new_day += 1
		action = self.env['ir.actions.act_window'].for_xml_id('calendar_appointment', 'spot_menu_action')
		action['domain'] = [('id', 'in', spot_ids)]
		# ~ _logger.warn(action)
		
		_logger.warn(event_list)
		return action
