# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import os
import xlrd


class ContactCustom(models.Model):
    _inherit = 'res.partner'

    nearest_land_mark = fields.Char()
    fax_number = fields.Char('Fax No.')
    # employee_id = fields.Many2one('hr.employee', string='Related Employee', index=True)
    employee_ids = fields.One2many('hr.employee', 'partner_id', string="Related Employee", auto_join=True)
    is_qshield_sponsor = fields.Boolean(string='Is Qshield Sponsor')
    check_qshield_sponsor = fields.Boolean(compute="compute_check_qshield_sponsor")
    is_address = fields.Boolean(string="Is Address", default=False)
    is_employee_create = fields.Boolean(string='Is Employee Create')
    job_id = fields.Many2one(comodel_name="hr.job", string="Job Position", required=False, )

    def update_invoice_type(self):
        file_path = os.path.dirname(os.path.dirname(__file__)) + '/data/Company Types.xlsx'
        with open(file_path, 'rb') as f:
            try:
                workbook = xlrd.open_workbook(file_path, on_demand=True)
                worksheet = workbook.sheet_by_index(0)
                first_row = []
                for col in range(worksheet.ncols):
                    first_row.append(worksheet.cell_value(0, col))
                data = []
                for row in range(1, worksheet.nrows):
                    elm = {}
                    for col in range(worksheet.ncols):
                        elm[first_row[col]] = worksheet.cell_value(row, col)
                    data.append(elm)
                for rec in data:
                    partner = self.sudo().search([('name', 'ilike', rec.get('Name')), ('active', 'in', [False, True])])
                    if partner:
                        if rec.get('Company Type') and rec.get('Company Type').capitalize() == 'Per transaction':
                            partner.write({'partner_invoice_type': 'per_transaction'})
                        elif rec.get('Company Type') and rec.get('Company Type').capitalize() == 'Retainer':
                            partner.write({'partner_invoice_type': 'retainer'})
                        elif rec.get('Company Type') and rec.get('Company Type').capitalize() == 'Partner':
                            partner.write({'partner_invoice_type': 'partners'})
                        elif rec.get('Company Type') and rec.get('Company Type').capitalize() == 'Outsourcing':
                            partner.write({'partner_invoice_type': 'outsourcing'})
                        elif rec.get('Company Type') and rec.get('Company Type').capitalize() == 'One time transaction':
                            partner.write({'partner_invoice_type': 'one_time_transaction'})
                        elif rec.get('Company Type') and rec.get(
                                'Company Type').capitalize() == 'Retainer, outsourcing':
                            partner.write({'partner_invoice_type': 'retainer'})
                        elif rec.get('Company Type') and rec.get('Company Type').capitalize() == "Please archive":
                            if partner.active:
                                partner.active = False
            except Exception as e:
                raise UserError(e)

    @api.depends('sponsor', 'person_type')
    def compute_check_qshield_sponsor(self):
        for rec in self:
            if rec.sponsor and rec.sponsor.is_qshield_sponsor and rec.person_type == 'emp':
                rec.check_qshield_sponsor = True
            else:
                rec.check_qshield_sponsor = False

    @api.onchange('sponsor.is_employee_create', 'sponsor', 'person_type')
    def _check_qshield_sponsor(self):
        for rec in self:
            if rec.sponsor and rec.sponsor.is_employee_create and rec.person_type == 'emp':
                rec.is_qshield_sponsor = True
            else:
                rec.is_qshield_sponsor = False

    @api.constrains('employee_ids')
    def _check_employee_length(self):
        for contact in self:
            if len(contact.employee_ids) > 1:
                raise ValidationError(
                    _('Only one employee link with contact'))

    @api.model
    def create(self, values):
        # Add code here
        res = super(ContactCustom, self).create(values)
        if self._context.get('from_employee'):
            return res
        else:
            if res.person_type == 'emp':
                res.create_employee()
            return res

    def write(self, vals):
        res = super(ContactCustom, self).write(vals)
        if res:
            if self.is_qshield_sponsor and self.person_type == 'emp' and 'active' in vals:
                if self.active:
                    employee = self.env['hr.employee'].search([('partner_id', '=', self.id), ('active', '=', False)])
                    if employee:
                        employee.write({'active': True})
                    else:
                        self.create_employee()
                else:
                    employee = self.env['hr.employee'].search([('partner_id', '=', self.id)])
                    if employee:
                        employee.write({'active': False})
            elif self.is_qshield_sponsor and self.person_type == 'emp':
                employee = self.env['hr.employee'].search([('partner_id', '=', self.id), ('active', '=', False)])
                if employee:
                    employee.write({'active': True})
                else:
                    self.create_employee()
            else:
                employee = self.env['hr.employee'].search([('partner_id', '=', self.id)])
                if employee:
                    employee.write({'active': False})
        return res

    def create_employee(self, partner=False, sponsor=False):
        for rec in self:
            if rec.is_qshield_sponsor:
                dependants = []
                if partner:
                    if not rec.employee_ids:
                        for each_dependant in rec.employee_dependants:
                            dependants.append((0, 0, {
                                'name': each_dependant.name,
                                'gender': each_dependant.gender,
                                'dob': each_dependant.date,
                            }))
                        partner_name_list = rec.name.split()
                        first_name = partner_name_list[0]
                        middle_name = ' '.join(partner_name_list[1:-1]) if len(partner_name_list) > 2 else ''
                        last_name = partner_name_list[-1] if len(partner_name_list) >= 2 else ''
                        employee = self.env['hr.employee'].create({
                            'name': rec.name,
                            'first_name': first_name,
                            'middle_name': middle_name,
                            'last_name': last_name,
                            'country_id': rec.nationality.id,
                            'gender': rec.gender,
                            'birthday': rec.date,
                            'work_phone': rec.phone,
                            'mobile_phone': rec.mobile,
                            'work_email': rec.email,
                            'dependant_id': dependants,
                            'partner_id': rec.id,
                            'work_in': rec.sponsor.id,
                            'job_title': rec.job_id.name if rec.job_id else False,
                            'iban_number': rec.iban_number,
                            'joining_date': rec.joining_date,
                            'is_out_sourced': True if rec.sponsor and rec.parent_id and rec.sponsor != rec.parent_id else False,
                            'related_company_id': rec.parent_id.id if rec.parent_id else False,
                            'passport_id': rec.passport_doc.document_number if rec.passport_doc else False,
                            'qid_number': rec.qatar_id_doc.document_number if rec.qatar_id_doc else False,
                            'job_id': rec.job_id.id if rec.job_id else False,
                        })
                else:
                    if sponsor and sponsor.is_employee_create or rec.sponsor.is_employee_create:
                        if not rec.employee_ids:
                            for each_dependant in rec.employee_dependants:
                                dependants.append((0, 0, {
                                    'name': each_dependant.name,
                                    'gender': each_dependant.gender,
                                    'dob': each_dependant.date,
                                }))
                            partner_name_list = rec.name.split()
                            first_name = partner_name_list[0]
                            middle_name = ' '.join(partner_name_list[1:-1]) if len(partner_name_list) > 2 else ''
                            last_name = partner_name_list[-1] if len(partner_name_list) >= 2 else ''
                            employee = self.env['hr.employee'].create({
                                'name': rec.name,
                                'first_name': first_name,
                                'middle_name': middle_name,
                                'last_name': last_name,
                                'country_id': rec.nationality.id,
                                'gender': rec.gender,
                                'birthday': rec.date,
                                'work_phone': rec.phone,
                                'mobile_phone': rec.mobile,
                                'work_email': rec.email,
                                'dependant_id': dependants,
                                'partner_id': rec.id,
                                'work_in': rec.sponsor.id,
                                'job_title': rec.job_id.name if rec.job_id else False,
                                'iban_number': rec.iban_number,
                                'joining_date': rec.date_join,
                                'is_out_sourced': True if rec.sponsor and rec.parent_id and rec.sponsor != rec.parent_id else False,
                                'related_company_id': rec.parent_id.id if rec.parent_id else False,
                                'passport_id': rec.passport_doc.document_number if rec.passport_doc else False,
                                'qid_number': rec.qatar_id_doc.document_number if rec.qatar_id_doc else False,
                                'job_id': rec.job_id.id if rec.job_id else False,
                            })
