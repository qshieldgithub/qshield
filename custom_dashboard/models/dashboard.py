# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, date


class ServiceRequest(models.Model):
    _inherit = 'ebs_mod.service.request'

    is_exceptional = fields.Boolean()
    is_escalated = fields.Boolean()
    is_overdue = fields.Boolean()
    is_governmental_fees = fields.Boolean()
    governmental_fees = fields.Integer()

    @api.onchange('is_escalated')
    @api.model
    def get_request(self, args=""):
        request_dict = {}
        status_dict = {
            'draft': 'Draft',
            'new': 'New',
            'progress': 'In Progress',
            'hold': 'On Hold',
            'complete': 'Completed',
            'reject': 'Rejected',
            'cancel': 'Canceled'
        }
        for key in status_dict:
            if args:
                domain = [('status', '=', key), ('date', '>=', args.get('date_from')),
                          ('date', '<=', args.get('date_to')), ('is_escalated', '=', False)]
            else:
                domain = [('status', '=', key), ('is_escalated', '=', False)]

            no_of_requests = self.env['ebs_mod.service.request'].search_count(domain)
            request_dict[key] = no_of_requests

        progress_overdue = self.env['ebs_mod.service.request'].search([('status', '=', 'progress')])
        for each in progress_overdue:
            if each.progress_date:
                today = date.today()
                if each.progress_date + timedelta(days=each.sla_days) > today:
                    each.is_overdue = True
        overdue = self.env['ebs_mod.service.request'].search_count([('is_overdue', '=', True),
                                                                    ('is_escalated', '=', False)])
        progress_normal = self.env['ebs_mod.service.request'].search_count([('status', '=', 'progress'),
                                                                            ('is_exceptional', '=', False),
                                                                            ('is_escalated', '=', False)])
        progress_exceptional = self.env['ebs_mod.service.request'].search_count([('status', '=', 'progress'),
                                                                                 ('is_exceptional', '=', True),
                                                                                 ('is_escalated', '=', False)])
        escalated = self.env['ebs_mod.service.request'].search_count([('is_escalated', '=', True)])
        request_dict['overdue'] = overdue
        request_dict['progress_normal'] = progress_normal
        request_dict['progress_out_of_scope'] = 0
        request_dict['progress_exceptional'] = progress_exceptional
        request_dict['escalated'] = escalated
        return request_dict


class ServiceRequestWorkFlow(models.Model):
    _inherit = 'ebs_mod.service.request.workflow'

    def _domain_drivers(self):
        job_ids = self.env['hr.job'].search([('name', 'in', ['PRO', 'Driver'])])
        return [('job_id', 'in', job_ids.ids)] if job_ids else []

    requires_driver = fields.Boolean()
    driver = fields.Many2one('hr.employee', string='Driver', domain=_domain_drivers)
    time_slot_type = fields.Selection([('7', '7:00 - 7:59 AM'),
                                       ('8', '8:00 - 8:59 AM'),
                                       ('9', '9:00 - 9:59 AM'),
                                       ('10', '10:00 - 10:59 AM'),
                                       ('11', '11:00 - 11:59 AM'),
                                       ('12', '12:00 - 12:59 PM'),
                                       ('1', '1:00 - 1:59 PM'),
                                       ('2', '2:00 - 2:59 PM'),
                                       ('3', '3:00 - 3:59 PM'),
                                       ('4', '4:00 - 4:59 PM'),
                                       ('5', '5:00 - 5:59 PM'),
                                       ('6', '6:00 - 6:59 PM')])
    delivery_date = fields.Date()
    destination_id = fields.Many2one('ebs_mod.service.destination', 'Destination Name')

    @api.onchange('driver', 'destination_id', 'delivery_date', 'time_slot_type')
    @api.depends('driver', 'destination_id', 'delivery_date', 'time_slot_type')
    def check_driver(self):
        if self.driver and self.destination_id and self.delivery_date and self.time_slot_type:
            check_date_slot = self.env['ebs_mod.service.request.workflow'].search([('driver', '=', self.driver.id),
                                                                                   ('delivery_date', '=',
                                                                                    self.delivery_date),
                                                                                   ('destination_id', '=',
                                                                                    self.destination_id.id),
                                                                                   ('time_slot_type', '=',
                                                                                    self.time_slot_type)])
            check_date_slot_count = self.env['ebs_mod.service.request.workflow'].search_count(
                [('driver', '=', self.driver.id),
                 ('delivery_date', '=',
                  self.delivery_date),
                 ('time_slot_type', '=',
                  self.time_slot_type)])
            if check_date_slot:
                my_error_msg = "The driver {} is assigned to another task on {} at {}. Destinations: ".format(
                    self.driver.name, self.delivery_date, self.time_slot_type)
                # previous_dest = ''
                # count = 0
                title = _("Take Care")
                for each_destination in check_date_slot:
                    # if count == check_date_slot_count:
                    #     break
                    # else:
                    #     previous_dest = each_destination.destination_id.name
                    my_error_msg += ' {},'.format(each_destination.destination_id.name)
                # count += 1
                # my_error_msg += ' {}'.format(previous_dest)
                # my_error_msg = _(my_error_msg)
                # return {
                #     'type': 'ir.actions.client',
                #     'tag': 'display_notification',
                #     'params': {
                #         'title': title,
                #         'message': my_error_msg,
                #         'sticky': False,
                #     }
                # }
                # popup = Popup(title='Test popup', content=Label(text='Hello world'), auto_dismiss=False)
                # popup.open()
            # title = _("Connection Test Succeeded!")
            # message = _("Everything seems properly set up!")
            # return {
            #     'type': 'ir.actions.client',
            #     'tag': 'display_notification',
            #     'params': {
            #         'title': title,
            #         'message': message,
            #         'sticky': False,
            #     }
            # }
        else:
            return False

    @api.model
    def get_request(self, args=""):
        request_list = []
        if args:
            domain = [('date', '>=', args.get('date_from')), ('date', '<=', args.get('date_to'))]
        else:
            domain = []
        employees = self.env['res.users'].search(domain)
        for each_employee in employees:
            domain = [('status', '=', 'progress'), ('assign_to', '=', each_employee.id)]
            no_of_requests = self.env['ebs_mod.service.request.workflow'].search_count(domain)
            if no_of_requests:
                request_dict = {
                    'employee_id': each_employee.id,
                    'employee_name': each_employee.name,
                    'employee_image': each_employee.image_1920,
                    'progress': no_of_requests
                }
                request_list.append(request_dict.copy())

        def get_progress(elem):
            return elem.get('progress')

        request_list.sort(key=get_progress, reverse=True)
        return request_list

    @api.model
    def get_driver(self, args=""):
        request_list = []
        job_ids = self.env['hr.job'].search([('name', 'in', ['PRO', 'Driver'])])
        drivers = self.env['hr.employee'].search([('job_id', 'in', job_ids.ids)])
        for each_driver in drivers:
            today = datetime.today()
            if args:
                domain = [('delivery_date', '=', args.get('date_day'))]
            else:
                domain = [('status', '=', 'progress'), ('driver', '=', each_driver.id),
                          ('delivery_date', '=', today)]
            destinations = self.env['ebs_mod.service.request.workflow'].search(domain)
            if destinations:
                request_dict = {
                    'driver_id': each_driver.id,
                    'driver_name': each_driver.name,
                    'destination': []
                }
                for each_destination in destinations:
                    request_dict['destination'].append({'destination': each_destination.destination_id.name,
                                                        'slot': each_destination.time_slot_type})
                request_list.append(request_dict.copy())
        return request_list


class ServiceTypes(models.Model):
    _inherit = 'ebs_mod.service.types'

    consolidation_id = fields.Many2one('ebs_mod.service.type.consolidation', 'Consolidation Name', store=True)


class ServiceDestination(models.Model):
    _name = 'ebs_mod.service.destination'

    name = fields.Char('Destination Name')


class ServiceTypeConsolidation(models.Model):
    _name = 'ebs_mod.service.type.consolidation'

    name = fields.Char('Consolidation Name')
    service_type = fields.One2many('ebs_mod.service.types', 'consolidation_id')

    @api.model
    def get_request(self):
        request_list = []
        consolidated = self.env['ebs_mod.service.type.consolidation'].search([])
        for each_consolidated in consolidated:
            domain = [('consolidation_id', '=', each_consolidated.id)]
            service_types = self.env['ebs_mod.service.types'].search(domain)
            no_of_all = 0
            for each_service_type in service_types:
                # print(each_service_type)
                domain = [('status', '=', 'progress'), ('service_type_id', '=', each_service_type.id)]
                no_of_inprogress = self.env['ebs_mod.service.request'].search_count(domain)
                no_of_all += no_of_inprogress
            if no_of_all:
                request_dict = {
                    'consolidated_service_id': each_consolidated.id,
                    'consolidated_service_name': each_consolidated.name,
                    'count': no_of_all
                }
                request_list.append(request_dict.copy())
        return request_list
