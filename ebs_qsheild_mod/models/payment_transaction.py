# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PaymentTransaction(models.Model):
    _name = 'ebs_mod.payment.transaction'
    _description = "Payment Transaction"

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        required=True)
    partner_type = fields.Selection(
        string='Contact Type', store=True,
        selection=[
            ('company', 'Company'),
            ('emp', 'Employee'),
            ('visitor', 'Visitor'),
            ('child', 'Dependent')],
        related="partner_id.person_type"
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        required=True)

    amount = fields.Float(
        string='Amount',
        required=True, default=0.0)
    date = fields.Datetime(
        string='Date',
        required=True)
    desc = fields.Text(
        string="Description",
        required=False)

    message = fields.Char(
        string='Message',
        required=False)

    trx_response_code_full = fields.Char(
        string='Response Code Full',
        required=False)
    trx_response_code = fields.Selection(
        string='Transaction Response',
        selection=[('0', 'Success'),
                   ('1', 'Error'), ],
        required=False)
    acq_response_code = fields.Char(
        string='ACQ Response Code',
        required=False)
    transaction_no = fields.Char(
        string='Transaction Number',
        required=False)
    batch_no = fields.Char(
        string='Batch Number',
        required=False)
    authorize_id = fields.Char(
        string='Authorized ID',
        required=False)

    def complete_payment(self):
        self.trx_response_code = "0"
        self.message = "Transaction Completed Manually"
        self.env['ebs_mod.contact.payment'].create({
            "transaction_id": self.id
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
