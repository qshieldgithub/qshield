# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime


class DocumentsCustom(models.Model):
    _inherit = 'documents.document'
    _order = 'issue_date desc'

    # _sql_constraints = [
    #     ('document_number_document_type_unique', 'unique (document_number,document_type_id)',
    #      'Document Number and Document Type Combination must be unique !'),
    # ]

    desc = fields.Text(
        string="Description",
        required=False)
    issue_date = fields.Date(
        string='Issued Date',
        required=False)
    expiry_date = fields.Date(
        required=False)

    document_number = fields.Char(
        string='Document Number',
        required=False)
    document_type_id = fields.Many2one(
        comodel_name='ebs_mod.document.types',
        string='Document Type',
        required=False)

    notify = fields.Boolean(
        string='Notified For Expiration',
        related='document_type_id.notify',
    )

    days_before_notifaction = fields.Integer(
        string='Days Before Expiration',
        related='document_type_id.days_before_notifaction',
    )

    status = fields.Selection(
        string='Status',
        selection=[('na', 'N/A'),
                   ('active', 'Active'), ('expired', 'Expired')],
        default='na',
        required=False, )

    service_id = fields.Many2one(
        comodel_name='ebs_mod.service.request',
        string='Service',
        required=False, tracking=True)

    related_company = fields.Many2one(
        comodel_name='res.partner',
        string='Related Company',
        store=True,
        related="partner_id.related_company")

    related_contact = fields.Many2one(
        comodel_name='res.partner',
        string='Related Contact',
        related="partner_id.parent_id")
    date_stop_renew = fields.Date(
        string='Do Not Renew After',
        required=False,
        related="partner_id.date_stop_renew")
    person_type = fields.Selection(
        string='Person Type',
        selection=[
            ('company', 'Company'),
            ('emp', 'Employee'),
            ('visitor', 'Visitor'),
            ('child', 'Dependent')],
        store=True,
        related="partner_id.person_type"
    )

    sponsor = fields.Many2one(
        comodel_name='res.partner',
        string='Sponsor',
        required=False,
        readonly=True,
        store=True,
        related="partner_id.sponsor")

    renewed = fields.Boolean(
        string='Renewed',
        required=False,
        default=False)

    @api.constrains('document_number')
    def _check_document_number(self):
        for rec in self:
            if len(self.env['documents.document'].search(
                    [('document_number', '=', rec.document_number), ('active', '=', True), ('id', '!=', rec.id)])) != 0:
                raise ValidationError(_("Document Number and Document Type Combination must be unique !"))

    def notify_expired_document(self):
        group_companies = self.read_group(
            domain=[('related_company_ro.account_manager', '!=', False)],
            fields=[],
            groupby=['related_company_ro'])
        for company in group_companies:
            documents = self.search([('active', '=', 'True'), ('renewed', '=', False),('notify', '=', True),
                                     ('related_company_ro', '=', company['related_company_ro'][0]), ])
            if documents:
                # expiry_date
                items = []
                account_manager = None
                company_name = None
                for document in documents:
                    company_name = document.related_company_ro.name
                    account_manager = document.related_company_ro.account_manager
                    items.append(
                        {
                            'Document_Number': document.document_number,
                            'Document_Type': document.document_type_id.name,
                            'Employee_Name ': document.partner_id.name,
                            'Employee_Type': document.partner_type,
                            'Expiration_Date': document.expiry_date,
                        }
                    )
                mail = self.env['mail.mail'].sudo().create({
                    'subject': _('Company {} / Documents Expiration.'.format(company_name)),
                    'email_from': self.env.user.partner_id.email,
                    'author_id': self.env.user.partner_id.id,
                    'email_to': account_manager.user_id.email,
                    'body_html': " Dear Company {}, \n\n ".format(company_name) +
                                 " This is the Content of Expired Document With Fully Detail \n\n" +
                                 str("{} / {} / {}/ {} is expiring on {} date.\n\n".format(
                                     doc['Employee_Name'], doc['Employee_Type'], doc['Document_Type'],
                                     doc['Document_Number'], doc['Expiration_Date']) for doc in items)
                    ,
                })
                mail.send()

    # def name_get(self):
    #     result = []
    #     for rec in self:
    #         if rec.type:
    #             if rec.type == 'binary':
    #                 if rec.document_number:
    #                     result.append((rec.id, rec.document_number))
    #                 else:
    #                     result.append((rec.id, rec.name))
    #             else:
    #                 result.append((rec.id, rec.name))
    #         else:
    #             result.append((rec.id, rec.name))
    #     return result

    def name_get(self):
        result = []
        for rec in self:
            rec_name = ""
            if rec.document_number:
                rec_name = rec.document_number
            else:
                rec_name = rec.name
            result.append((rec.id, rec_name))
        return result

    def write(self, vals):
        # if vals.get('expiry_date', False):
        #     expiry_date = datetime.strptime(vals['expiry_date'], "%Y-%m-%d").today().date()
        #     if expiry_date > datetime.today().date():
        #         vals['status'] = 'active'
        #     else:
        #         vals['status'] = 'expired'
        res = super(DocumentsCustom, self).write(vals)
        if self.expiry_date and self.issue_date:
            if self.expiry_date < self.issue_date:
                raise ValidationError(_("Expiry date is before issue date."))
        return res

    def check_document_expiry_date(self):
        for doc in self.env['documents.document'].search([('status', '=', 'active')]):
            if doc.expiry_date:
                if doc.expiry_date < datetime.today().date():
                    doc.status = 'expired'

    @api.model
    def create(self, vals):
        if vals.get('expiry_date', False):
            expiry_date = datetime.strptime(vals['expiry_date'], "%Y-%m-%d").date()
            if expiry_date > datetime.today().date():
                vals['status'] = 'active'
            else:
                vals['status'] = 'expired'
        else:
            vals['status'] = 'na'
        res = super(DocumentsCustom, self).create(vals)
        if res.expiry_date and res.issue_date:
            if res.expiry_date < res.issue_date:
                raise ValidationError(_("Expiry date is before issue date."))
        return res

    def preview_document(self):
        self.ensure_one()
        action = {
            'type': "ir.actions.act_url",
            'target': "_blank",
            'url': '/documents/content/preview/%s' % self.id
        }
        return action

    def access_content(self):
        return super(DocumentsCustom, self).access_content()


class DocumentsFolderCustom(models.Model):
    _inherit = 'documents.folder'
    is_default_folder = fields.Boolean(
        string='Is Default Folder',
        required=False
    )
