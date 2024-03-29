# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
        return result

    def _compute_loan_amount(self):
        # print("==============_compute_loan_amount================================",self)
        total_paid = 0.0
        for loan in self:
            for line in loan.loan_lines:
                # print("====================", line.paid)
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid
            print(total_paid)

    # def _get_current_login_user(self):
    #
    #     user_obj = self.env['res.users'].search([])
    #
    #     for user_login in user_obj:
    #
    #         current_login = self.env.user
    #
    #         if user_login == current_login:
    #             self.processing_staff = current_login
    #     return

    name = fields.Char(string="Loan Name", default="/", readonly=True, help="Name of the loan")
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True, help="Date")
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True, help="Employee")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department", help="Employee")
    installment = fields.Integer(string="No Of Installments", default=1, help="Number of installments")
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today(), help="Date of "
                                                                                                             "the "
                                                                                                             "paymemt")
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, help="Company",
                                 default=lambda self: self.env.user.company_id,
                                 states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, help="Currency",
                                  default=lambda self: self.env.user.company_id.currency_id)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True, string="Job Position",
                                   help="Job position")
    loan_amount = fields.Float(string="Loan Amount", required=True, help="Loan amount")
    total_amount = fields.Float(string="Total Amount", store=True, readonly=True, compute='_compute_loan_amount',
                                help="Total loan amount")
    balance_amount = fields.Float(string="Balance Amount", store=True, compute='_compute_loan_amount',
                                  help="Balance amount")
    # total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute='_compute_loan_amount',
    #                                  help="Total paid amount")
    total_paid_amount = fields.Float(string="Total Paid Amount", store=True, compute="get_paid_amount",
                                     help="Total paid amount")

    hr_approve_user = fields.Char(string="")
    finance_approve_user = fields.Char(string="Loan Name")
    management_approve_user = fields.Char(string="Loan Name")
    approved_by = fields.Char(string="Approved by")

    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('waiting_approval_1', 'Submitted'),
    #     ('first_approve', 'First Approved'),
    #     ('approve', 'Second Approved'),
    #     ('refuse', 'Refused'),
    #     ('cancel', 'Canceled'),
    # ], string="State", default='draft', track_visibility='onchange', copy=False, )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'HR'),
        ('first_approve', 'Finance'),
        ('second_approve', 'Management'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )
    purpose_of_advance = fields.Char(string='Purpose of Advance')
    user_id = fields.Many2one('res.users', string='Approved By')

    @api.model
    def create(self, values):
        # res = super(HrLoan, self).create(values)

        employee_id = self.env['hr.employee'].browse(values['employee_id'])

        loan_count = self.env['hr.loan'].search_count(
            [('employee_id', '=', values['employee_id']), ('state', '=', 'approve'),
             ('balance_amount', '!=', 0)])
        print(loan_count)
        if loan_count:
            raise ValidationError(_("The employee has already a pending installment"))
        else:
            # values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
            values['name'] = self.env['ir.sequence'].next_by_code('hr.loan.seq') or ' '

        return super(HrLoan, self).create(values)

    def compute_installment(self):
        # print("======compute_installment===========================",self)
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
            loan._compute_loan_amount()

        return True

    @api.onchange('loan_lines', 'total_paid_amount')
    @api.depends('loan_lines', 'total_paid_amount')
    def get_paid_amount(self):
        # print("==============_compute_loan_amount================================",self)
        total_paid = 0.0
        for line in self.loan_lines:
            # print("====================", line.paid)
            if line.paid:
                total_paid += line.amount

        self.total_paid_amount = total_paid
        self.balance_amount = self.total_amount - self.total_paid_amount

    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_submit(self):
        if not self.loan_amount:
            raise ValidationError(_("Please Enter Loan Amount"))
        self.write({'state': 'waiting_approval_1'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_first_approve(self):
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({'state': 'first_approve'})
        self.hr_approve_user = self.env.user.name
        self.approved_by = self.hr_approve_user

    def action_second_approve(self):
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({'state': 'second_approve'})
        self.finance_approve_user = self.env.user.name
        self.approved_by += ', ' + self.env.user.name

    def action_approve(self):
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({
                    'state': 'approve',
                    'user_id': self.env.user,
                })
        self.management_approve_user = self.env.user.name
        self.approved_by += ', ' + self.env.user.name

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    'You cannot delete a loan which is not in draft or cancelled state')
        return super(HrLoan, self).unlink()


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True, help="Date of the payment")
    employee_id = fields.Many2one('hr.employee', string="Employee", help="Employee")
    amount = fields.Float(string="Amount", required=True, help="Amount")
    paid = fields.Boolean(string="Is Paid ?", help="Paid")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.", help="Loan")
    # payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.", help="Payslip")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

    loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')
    payslip_count = fields.Integer(string="Payslip Count", compute="_compute_employee_payslip")

    def _compute_employee_payslip(self):
        self.payslip_count = self.env['qshield.payslip'].search_count([('employee_id', '=', self.id)])

    def get_employee_payslips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payslips',
            'view_mode': 'tree,form',
            'res_model': 'qshield.payslip',
            'domain': [('employee_id', '=', self.id)],
            'context': "{'create': True}"
        }
