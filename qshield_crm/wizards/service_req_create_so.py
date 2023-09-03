# -*- coding: utf-8 -*-from odoo import models, fields, api, _from odoo.exceptions import ValidationErrorclass CreateMultipleInvoice(models.TransientModel):    _name = 'create.service.sale.order'    _description = "Create Sale Order From Service"    service_price = fields.Float(string="Enter Amount approved by Client", required=True)    def generate_sale_order(self):        self.ensure_one()        service_id = self._context.get('active_id')        service_obj = self.env['ebs_mod.service.request'].browse(service_id)        if service_obj and service_obj.is_out_of_scope or service_obj.is_one_time_transaction:            order_id = service_obj.env['sale.order'].sudo().create({                'partner_id': service_obj.partner_id.id,                'account_manager': service_obj.partner_id.account_manager.id if service_obj.partner_id.account_manager else False,                'is_out_of_scope': True,                'generate_order_line': 'from_consolidation',                'is_agreement': 'one_time_payment' if service_obj.is_one_time_transaction else 'is_retainer',                # 'order_line': [(0, 0, {                #     'product_id': service_obj.service_type_id.variant_id.product_id.id,                #     'name': service_obj.service_type_id.variant_id.product_id.name,                #     'product_uom_qty': 1,                #     'price_unit': service_obj.service_type_id.variant_id.product_id.lst_price,                # })]            })            if order_id:                description = ''                name = ''                price_unit = 0                product_id = False                if service_obj.service_type_id and service_obj.service_type_id.product_id:                    description += service_obj.service_type_id.name                    product_id = service_obj.service_type_id.product_id.id                    price_unit += service_obj.service_type_id.product_id.lst_price                elif service_obj.service_type_id:                    description += service_obj.service_type_id.name                    obj = self.env['product.product'].create({'name': service_obj.service_type_id.name})                    if obj:                        product_id = obj.id                        service_obj.write({'product_id': obj.id})                service_obj.write({'sale_order_id': order_id.id})                order_id.sudo().write({'order_line': [(0, 0, {                    'display_type': 'line_section',                    'name': description                    # 'name': service_obj.service_type_id and service_obj.service_type_id.variant_id and service_obj.service_type_id.variant_id.consolidation_id.name                })]})                order_id.sudo().write({'order_line': [(0, 0, {                    'product_id': product_id,                    'name': description,                    'product_uom_qty': 1,                    'price_unit': price_unit,                })]})                if service_obj.partner_invoice_type in ['partners', 'per_transaction']:                    payment_term_id = service_obj.env.ref('account.account_payment_term_immediate').id                    # approvers = order_id.mapped('approver_ids').filtered(                    #     lambda approver: approver.status != 'approved')                    # if len(approvers) > 0:                    #     for approver in approvers:                    #         approver.sudo().write({'status': 'approved', 'approval_date': datetime.now()})                    order_id.sudo().write({'state': 'sale', 'payment_term_id': payment_term_id})                    if order_id.opportunity_id:                        order_id.sudo().write({'state': 'submit_client_operation'})                        order_id.opportunity_id.action_set_won_rainbowman()                        msg = (_('Opportunity Won {}'.format(order_id.opportunity_id.name)))                        order_id.message_post(body=msg)                    service_obj.request_submit()                    if service_obj.invoice_term_start_date and service_obj.invoice_term_end_date:                        order_id.sudo().write(                            {'start_date': service_obj.invoice_term_start_date,                             'end_date': service_obj.invoice_term_end_date})                        order_id.sudo().action_create_invoice_term()                order_id.action_confirm()                order_id.action_create_invoice_term()            notify_users = self.env.ref('sales_team.group_sale_salesman').users            for user in notify_users:                order_id.activity_schedule(                    'qshield_crm.mail_activity_quotation',                    user_id=user.id)    @api.constrains('service_price')    def _check_service_price_exist(self):        for rec in self:            if not rec.service_price:                raise ValidationError(_("Please Insert Amount approved by Client ....."))