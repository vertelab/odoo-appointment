import odoo
from odoo import api, fields, models, _, http
from odoo.exceptions import UserError, Warning
import logging
from datetime import timedelta, time
import odoo.http as http
from odoo.http import request
import hashlib
from odoo.api import Environment as Env

_logger = logging.getLogger(__name__)

class calendar_attendee(models.Model):
    _name = 'calendar.appointment.attendee'

    appointment_id = fields.Many2one(comodel_name='calendar.appointment', required=True, ondelete='cascade')
    partner_id = fields.Many2one(comodel_name='res.partner', required=True, ondelete='cascade')
    #token = fields.Char() Ny Tokenhantering i framtiden ska ske här


class calendar_appointment(models.Model):

    _name = 'calendar.appointment' # Kan förekommer i dropdown t ex
    _description = 'Appointments for calendar'

    def default_user(self):
        return self.env.user

    name = fields.Char(string = 'Name')
    attendee_ids = fields.Many2many(comodel_name ='res.partner') # Comodel_name
    # ~ product_ids = fields.Many2many(comodel_name = 'product.product') # I detta fall vilken massage som ska bokas in, vi behöver veta duration på produkten.
    spot_ids = fields.One2many(comodel_name = 'calendar.appointment.spot', inverse_name = 'appointment_id')
    user_id = fields.Many2one(comodel_name = 'res.users', required=True, default=default_user)
    is_published = fields.Boolean(string = 'Publish') # String represents a label
    description = fields.Text(string = 'Descriptions')
    meeting_type = fields.Selection([('One2one', 'One to One'),('Many2one', 'Many to One'),], string = 'Type Selections', required=True) # Ena värdet visa i dropdown och andra lagras i DB:n
    date_due = fields.Date(string = 'Date Due')
    token = fields.Char()
    calendar_attendee_ids = fields.Many2many(comodel_name='calendar.appointment.attendee', compute='_compute_calendar_attendee_ids')

    """
       When 'send invite' button is pressed it generates a new calendar_attendee for each attendee_ids in an appointment.

       When pressed multiple times it generates the calendar_attendees equal amount of times.
       This creates problems in usercase 1 (line 224) as there can only be one calendar_attendee per attendee.
       A new compute_calendar_attendee_ids should run on @api.depends but seems to trigger only by the 'send invite' button.
    """
    @api.depends('attendee_ids')
    def _compute_calendar_attendee_ids(self):
        for attendee in self.calendar_attendee_ids:
            if attendee.partner_id not in self.attendee_ids:
                attendee.unlink()
        attendees = self.calendar_attendee_ids.mapped('partner_id')
        for attendee in self.attendee_ids:
            if attendee not in attendees:
                self.calendar_attendee_ids |= self.env['calendar.appointment.attendee'].create({
                    'appointment_id': self.id,
                    'partner_id': attendee.id,
                    #'token': 'En ny token!',
                })

    """
    Sends the mail invitation at the creation of an event by clicking the button in the top left corner.
    """
    @api.multi
    def send_invitation_template(self):
        if self.meeting_type == 'One2one':
            template = self.env.ref('calendar_appointment.invitation_model')
            for attendee in self.calendar_attendee_ids:
                template.send_mail(attendee.id)
        elif self.meeting_type == 'Many2one':
            template = self.env.ref('calendar_appointment.meeting_invitation_model')
            for attendee in self.calendar_attendee_ids:
                template.send_mail(attendee.id)

    @api.onchange('token')
    def create_token(self):
            self.token = hashlib.sha1(bytes(str(self.id), 'utf-8')).hexdigest()

    def date_due_scheduled_action(self):
        appointments = self.env['calendar.appointment'].search([('date_due', '<=', fields.Date.today())])
        template = self.env.ref('calendar_appointment.meeting_booking_model')
        for appointment in appointments:
            
            template.send_mail(appointment.id)


class calendar_appointment_spot(models.Model):

    _name = 'calendar.appointment.spot'
    _description = 'Spot for calendars appointment'

    name = fields.Char(string='Name', required=True)
    appointment_id = fields.Many2one(comodel_name='calendar.appointment')
    partner_ids = fields.Many2many(comodel_name='res.partner')
    event_id = fields.Many2one(comodel_name='calendar.event')
    note = fields.Text(string='Note field')
    date_start = fields.Datetime(string = 'Date start')
    duration = fields.Float(string = 'Duration')
    date_end = fields.Datetime(string = 'Date End')

    """Methods creating the desired date format for our viewmodel"""
    def date_end_template_format(self):
        return self.date_end.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    def date_start_template_format(self):
        return self.date_start.strftime("%Y-%m-%dT%H:%M:%S+00:00")


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

    @api.multi
    def create_spots(self):
        spots_created = 0
        appointment = self._default_appointment()
        spot_ids = []
        divider = 1
        current_startdate = self.date_start

        if not appointment and appointment.user_id:
                raise Warning(_('Appointment or user missing, please choose an appointment and user'))

        """
        Loops through desired number of spots, creates them one after another.
        Skips past already existing events.

        """
        days_counter = 0
        while spots_created < self.nmbr_spots:
            if self.nmbr_spots_per_day == spots_created/divider:
                days_counter += 1
                current_startdate = self.date_start + timedelta(days = days_counter)
                divider += 1

            current_stopdate = current_startdate + timedelta(hours=self.duration)

            colliding_events = self.env['calendar.event'].search([
            "&",
                ('start_datetime', '<=', current_startdate),
                ('stop_datetime', '>=', current_startdate),
            "|",
                ('start_datetime', '<=', current_stopdate),
                ('stop_datetime', '>=', current_stopdate)])

            colliding_spots = self.env['calendar.appointment.spot'].search([
            ('appointment_id', '=', appointment.id),
            "&",
                ('date_start', '<=', current_startdate),
                ('date_end', '>=', current_startdate),
            "|",
                ('date_start', '<=', current_stopdate),
                ('date_end', '>=', current_stopdate)])

            if current_stopdate > self.date_stop:
                """ Alert(Det fanns inte fler lediga tillfällen.)"""
                break

            if not colliding_events and not colliding_spots:
                spot_ids.append(self.env['calendar.appointment.spot'].create({
                'name' : 'spot',
                'date_start' : current_startdate,
                'date_end' : current_startdate + timedelta(hours=self.duration),
                'appointment_id' : self._context.get('active_id'),
                'duration' : self.duration}).id)
                spots_created += 1

            current_startdate += timedelta(hours=self.duration, minutes=5)

        action = self.env['ir.actions.act_window'].for_xml_id('calendar_appointment', 'spot_menu_action')
        action['domain'] = [('id', 'in', spot_ids)]

        return action


class MyController(http.Controller):

    """ First usercase"""
    @http.route('/appointment/<int:appointment_id>/<int:attendee_id>/<string:token>', type="http", website=True, auth='public')
    def handler(self, appointment_id, token, attendee_id):
        handler = http.request.env['calendar.appointment.spot'].sudo().search([('appointment_id', '=', appointment_id)])
        token_check = http.request.env['calendar.appointment'].sudo().search([('token', '=', token),('id', '=', appointment_id)])
        partner_check = token_check.attendee_ids.filtered(lambda a : a.id == attendee_id)

        if not partner_check.id:
            return request.not_found()

        if not token_check:
            return request.not_found()

        return http.request.render('calendar_appointment.appointment_booking', {'spots':handler, 'appointment' : token_check, 'partner' : partner_check})
    """
       First and Second usercase, the booking confirmation for both usercases.
       Sends email confirmation depending on the usercase.
    """
    @http.route('/appointment/spot', type="http", website=True, auth='public')
    def spot(self, **post):
        post.get("spot_id")
        token = post.get("token")
        attendee_id = post.get("attendee_id")

        spot = http.request.env['calendar.appointment.spot'].sudo().browse(int(post.get("spot_id")))
        appointment = http.request.env['calendar.appointment'].sudo().search([('id', '=', spot.appointment_id.id)])
        attendee = http.request.env['res.partner'].sudo().browse(int(post.get("attendee_id")))
        
        
        
        
        if appointment.meeting_type == 'One2one':
            event = http.request.env['calendar.event'].sudo().create({'start' : spot.date_start,
            'stop' : spot.date_end,
            'name' : "One2One Event",  # Fix calendar.appointment.spot.name and use as input
            'user_id' : appointment.user_id.id,
            'partner_ids' : [(4, attendee.id, 0), (4, appointment.user_id.partner_id.id, 0)]})

            calendar_attendee = http.request.env['calendar.appointment.attendee'].search([('partner_id', '=', attendee.id)])
            template = http.request.env.ref('calendar_appointment.notify_creator')
            template.send_mail(calendar_attendee.id)
            

        elif appointment.meeting_type == 'Many2one':
            event = http.request.env['calendar.event'].sudo().create({'start' : spot.date_start,
           'stop' : spot.date_end,
           'name' : "One2Many Event",
           'user_id' : appointment.user_id.id,
           'partner_ids' : [(6, 0 , appointment.attendee_ids.ids), (4, appointment.user_id.partner_id.id, 0)]})

            template = http.request.env.ref('calendar_appointment.notify_attendees')
            calendar_attendees = http.request.env['calendar.appointment.attendee'].search([('appointment_id', '=', appointment.id)])

            for calendar_attendee in calendar_attendees:
                template.send_mail(calendar_attendee.id)

        spot.event_id = event.id

        return http.request.render('calendar_appointment.confirmed_booking', {'spot': spot})

        """Second Usercase"""
    @http.route('/meeting/<int:appointment_id>/<int:attendee_id>/<string:token>', type="http", website=True, auth='public')
    def project_meeting_handler(self, appointment_id, attendee_id, token):

        project_meeting_handler = http.request.env['calendar.appointment.spot'].sudo().search([('appointment_id', '=', appointment_id)])
        token_check = http.request.env['calendar.appointment'].sudo().search([('token', '=', token),('id', '=', appointment_id)])
        partner_check = token_check.attendee_ids.filtered(lambda a : a.id == attendee_id)
        # ~ raise Warning('Partner_check.id: %s token_check.attendee_ids: %s attendee_id: %s'%(partner_check.id, token_check.attendee_ids, attendee_id))


        if not partner_check:
            return request.not_found()

        if not token_check:
            return request.not_found()


        return http.request.render('calendar_appointment.meeting_booking', {'spots': project_meeting_handler, 'appointment' : token_check, 'partner' : partner_check})

        """Second Usercase"""
    @http.route('/meeting/spot', type="http", website=True, auth="public")
    def handler_meeting(self, **post):
        post.get("spot_ids")
        post.get("token")
        post.get("attendee_id")



        spot_ids = [int(s) for s in post.get("spot_ids").split(',')]
        spots = []

        attendee = http.request.env['res.partner'].sudo().browse(int(post.get("attendee_id")))

        for spot_id in spot_ids:
            spot = http.request.env['calendar.appointment.spot'].sudo().browse(spot_id)

            spots += spot

            spot.write({'partner_ids' : [(4, attendee.id, 0)]})



        return http.request.render('calendar_appointment.meeting_confirmed_booking', {'spots' : spots})

    """Second Usercase"""
    @http.route('/meeting/booking/<int:appointment_id>/<int:attendee_id>/<string:token>', type="http", website=True, auth='public')
    def handler_meeting_booking(self, appointment_id, attendee_id, token):
        attendee = http.request.env['res.partner'].sudo().browse(attendee_id)
        token_check = http.request.env['calendar.appointment'].sudo().search([('token', '=', token),('id', '=', appointment_id)])

        # ~ raise Warning('Partner_check.id: %s token_check.attendee_ids: %s attendee_id: %s'%(partner_check.id, token_check.attendee_ids, attendee_id))



        if not token_check.user_id.partner_id.id == attendee.id:
            return request.not_found()

        if not token_check:
            return request.not_found()

        spots_to_use = []
        i = 0
        for spot in token_check.spot_ids.sorted(key=lambda s: len(s.partner_ids), reverse=True):
            i += 1
            spots_to_use.append(spot)
            if i >= 10:
               break



        return http.request.render('calendar_appointment.meeting_final_booking', {'spots' : spots_to_use, 'appointment' : token_check, 'partner' : token_check.user_id.partner_id})



