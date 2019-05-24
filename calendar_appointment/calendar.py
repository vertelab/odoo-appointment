import odoo
from odoo import api, fields, models, _, http
from odoo.exceptions import UserError, Warning
import logging
from datetime import timedelta, time
import odoo.http as http
from odoo.http import request
import hashlib

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
    attendee_ids_str = fields.Char(compute='compute_attendee_ids_str')
    token = fields.Char() # anropar metoden när ett nytt recordset skapas

    def compute_attendee_ids_str(self):
        self.attendee_ids_str = ','.join([str(a.id) for a in self.attendee_ids])
    
    @api.multi
    def send_invitation_template(self):
        template = self.env.ref('calendar_appointment.invitation_model')
        template.send_mail(self.id)
    
    @api.onchange('token')
    def _create_token(self):
        self.token = hashlib.sha1(bytes(str(self.id), 'utf-8')).hexdigest()
    # onchange, default
        
        
        
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
    # ~ date_start_hh_mm = date_start.strftime("%h:%m")
    # ~ date_end_hh_mm = date_end.strftime("%h:%m")
    
    def date_end_template_format(self):
        return self.date_end.strftime("%Y-%m-%dT%H:%M:%S")
        
    def date_start_template_format(self):
        return self.date_start.strftime("%Y-%m-%dT%H:%M:%S")
        
    def get_weekday(self):
        return self.date_start.weekday()
    
class calendar_event(models.Model):
    
    _inherit = 'calendar.event'
    
    
    appointment_id = fields.Many2one(comodel_name='calendar.appointment')
    

class Wizard(models.TransientModel):
    _name = 'calendar.appointment.wizard'
    _description = 'Wizard for adding spots'
    
    def _default_appointment(self):
        return self.env['calendar.appointment'].browse(self._context.get('active_id'))
    
    date_start = fields.Datetime(string='Start Date', required=True)
    date_stop = fields.Datetime(string='Stop Date', required=True)
    duration = fields.Float(string='Duration')
    nmbr_spots = fields.Integer(string='Number of Spots')
    nmbr_spots_per_day = fields.Integer(string='Number of spots per day')
    
    @api.one
    def test_function(self):
        appointment = self._default_appointment()
        if not appointment and appointment.user_id:
            raise Warning(_("appointment or user missing, please choose an appointment and user"))
        
        event_list = self.env['calendar.event'].search([('start_date','>=',self.date_start), ('stop_date', '<=',self.date_stop), ('user_id', '=', appointment.user_id.id)])
        event_list2 = self.env['calendar.event'].search([])
                
                # ~ filtered_list = spot_list.filtered(lambda r: r.event_list.contains())
        
        raise Warning("hej %s %s %s %s %s %s %s"% (union_list, intersect_list, event_list, event_list2, self.date_start, self.date_stop, appointment.user_id))
            
    @api.multi
    def create_spots(self):
        spots_created = 0
        appointment = self._default_appointment()
        # ~ event_list = self.env['calendar.event'].search([('start_date','>=',self.date_start), ('stop_date', '<=',self.date_stop), ('user_id', '=', appointment.user_id.id)])
        spot_ids = []
        divider = 1
        current_startdate = self.date_start
        
        if not appointment and appointment.user_id:
                raise Warning(_('Appointment or user missing, please choose an appointment and user'))
                
        days_counter = 0
        i = 0
        while spots_created < self.nmbr_spots:
            if self.nmbr_spots_per_day == spots_created/divider:
                days_counter += 1 
                current_startdate = self.date_start + timedelta(days = days_counter)
                divider += 1
                
            colliding_spots = self.env['calendar.event'].search([
                ('start_datetime', '>=', current_startdate),
                ('stop_datetime', '<=', current_startdate),
                "&",
                ('start_datetime', '<=', self.date_stop),
                ('stop_datetime', '>=', self.date_stop)])
                
                
            if not colliding_spots:
                spot_ids.append(self.env['calendar.appointment.spot'].create({
                'date_start' : current_startdate,
                'date_end' : current_startdate + timedelta(hours=self.duration),
                'appointment_id' : self._context.get('active_id'),
                'duration' : self.duration}).id)
                i += 1
            
            current_startdate += timedelta(hours=self.duration)
            
            spots_created += 1
                
            
        action = self.env['ir.actions.act_window'].for_xml_id('calendar_appointment', 'spot_menu_action')
        action['domain'] = [('id', 'in', spot_ids)]
        
        
        
        return action
        
        
                # Nuvarande tiden för en spot att skapas på. 
                # ~ spot_starttime = self.date_start + timedelta(hours=((spots_per_day_i) * self.duration), days=new_day)   
                # ~ spot_endtime = spot_starttime + timedelta(hours=(self.duration))
                
class MyController(http.Controller):
    @http.route('/appointment/<int:appointment_id>/<string:token>', type="http", website=True, auth='public')
    def handler(self, appointment_id, token):
        handler = http.request.env['calendar.appointment.spot'].sudo().search([('appointment_id', '=', appointment_id)])
        
        token_check = http.request.env['calendar.appointment'].sudo().search([('token', '=', token),('id', '=', appointment_id)])
        
        if not token_check:
            return request.not_found()
        
        return http.request.render('calendar_appointment.appointment_booking', {'spots':handler})
        
    @http.route('/appointment/spot/<string:token>', type="http", website=True, auth='public')
    def spot(self, **post):
        post.get("spot_id")
        
        spot = http.request.env['calendar.appointment.spot'].sudo().browse(int(post.get("spot_id")))
                
        token_check = http.request.env['calendar.appointment'].sudo().search([('token', '=', token),('id', '=', spot.appointment_id.id)])
        
        if not token_check:
            return request.not_found()
        
        return http.request.render('calendar_appointment.confirmed_booking', {'spot': spot})
        

    # ~ @http.route(['/appointment/json_test'], type='json', auth="public")
    # ~ def json_test(self):
        # ~ return [1, 2, 5, {'a': 2}]
