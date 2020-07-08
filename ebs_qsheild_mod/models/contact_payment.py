# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ContactPayment(models.Model):
    _name = 'ebs_mod.contact.payment'
    _description = "contact payment"

    transaction_id = fields.Many2one(
        comodel_name='ebs_mod.payment.transaction',
        string='Transaction',
        required=False)

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contact',
        related='transaction_id.partner_id')
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
        related='transaction_id.currency_id')

    amount = fields.Float(
        string='Amount',
        related='transaction_id.amount')
    service_id = fields.Many2one(
        comodel_name='ebs_mod.service.request',
        string='Service',
        required=False,related='transaction_id.service_id')
    desc = fields.Text(
        string="Description",
        required=False)
