from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.osv.expression import OR
from datetime import datetime
import binascii
import hmac
import hashlib
import json
import re
import uuid
import array


class ContactPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(ContactPortal, self)._prepare_portal_layout_values()
        values['payment_count'] = request.env['ebs_mod.contact.payment'].search_count(
            [('partner_id', '=', request.env.user.partner_id.id)])
        if values.get('sales_user', False):
            values['title'] = _("Salesperson")
        return values

    @http.route(['/my/payments', '/my/payments/page/<int:page>'], type='http', auth="user", website=True)
    def my_contact_payment(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content',
                           **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        domain = [('partner_id', '=', user.partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'date_desc': {'label': _('Oldest'), 'order': 'create_date asc'},
        }
        searchbar_inputs = {
            'desc': {'input': 'desc', 'label': _('Description')}
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = []
        # archive_groups = self._get_archive_groups('ebs_mod.contact.payment', domain)
        # if date_begin and date_end:
        #     domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in == 'desc':
                search_domain = OR([search_domain, [('desc', 'ilike', search)]])
            domain += search_domain

        # pager
        payment_count = request.env['ebs_mod.contact.payment'].search_count(domain)
        pager = portal_pager(
            url="/my/payments",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=payment_count,
            page=page,
            step=self._items_per_page
        )

        payments = request.env['ebs_mod.contact.payment'].search(domain, order=order, limit=self._items_per_page,
                                                                 offset=pager['offset'])
        request.session['my_payments_history'] = payments.ids[:100]
        values.update({
            'date': date_begin,
            'payments': payments,
            'page_name': 'payment',
            'default_url': '/my/payments',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("ebs_qsheild_mod.portal_contact_payment", values)

    @http.route(['/my/payments/insert_form'], type='http', auth='user', website=True)
    def contact_payment_insert_form(self):

        values = {
            'page_name': 'payment_insert',
            'currency': request.env.company.currency_id
        }

        return request.render("ebs_qsheild_mod.portal_contact_payment_form", values)

    @http.route(['/my/payments/return_url'], type='http', auth='user', method=['GET'], website=True)
    def payments_return_url(self, **kw):
        amount = request.params['vpc_Amount']
        order_info = request.params['vpc_OrderInfo']
        message = request.params['vpc_Message']
        trx_response_code = request.params.get('vpc_TxnResponseCode', False)
        vpc_receipt_no = request.params.get('vpc_ReceiptNo', False)
        acq_response_code = request.params.get('vpc_AcqResponseCode', False)
        transaction_no = request.params.get('vpc_TransactionNo', False)
        batch_no = request.params.get('vpc_BatchNo', False)
        authorize_id = request.params.get('vpc_AuthorizeId', False)

        transaction = request.env['ebs_mod.payment.transaction'].search([('order_info', '=', order_info)],
                                                                        limit=1)
        vals = {
            'message': message
        }
        if trx_response_code:
            vals['trx_response_code_full'] = trx_response_code
            if trx_response_code[0] == '0':
                vals['trx_response_code'] = '0'
            else:
                vals['trx_response_code'] = '1'
        else:
            vals['trx_response_code_full'] = '1'
            vals['trx_response_code'] = '1'

        if acq_response_code:
            vals['acq_response_code'] = acq_response_code
        if transaction_no:
            vals['transaction_no'] = transaction_no
        if vpc_receipt_no:
            vals['vpc_receipt_no'] = vpc_receipt_no
        if batch_no:
            vals['batch_no'] = batch_no
        if authorize_id:
            vals['authorize_id'] = authorize_id

        transaction.sudo().write(vals)

        if transaction.trx_response_code == "0":
            request.env['ebs_mod.contact.payment'].create({
                "transaction_id": transaction.id
            })

        return request.redirect('/my/payments')

    @http.route(['/my/payments/secure_token'], type='http', auth='user', method=['GET'], website=True)
    def payment_secure_token(self, **kw):
        with_token = False
        if request.params.get('token', False):
            if len(request.params['token']) == 51:
                with_token = True
        if with_token:
            env = request.env
            amount1 = request.params['amount1']
            amount2 = request.params['amount2']
            x = re.search("^[0 9]{2}$", amount2)
            if not x:
                return json.dumps({'status': "error", 'msg': _("Second field must be 2 digits only")})

            y = re.search("^\d+$", amount1)
            if not y:
                return json.dumps({'status': "error", 'msg': _("First field must be digits only")})

            amount = str(amount1) + str(amount2)
            host_url = request.httprequest.host_url
            # w = re.search("localhost", host_url)
            # if not x:
            return_url = host_url + "my/payments/return_url"
            # return_url = "http://jaafarkhansa.com/demo/gateway/index.php"
            # else:
            #     return_url = "http://jaafarkhansa.com/demo/gateway/index.php"
            transaction = env['ebs_mod.payment.transaction'].sudo().create(
                {
                    "partner_id": request.env.user.partner_id.id,
                    "currency_id": env['res.currency'].search([('name', '=', 'QAR')], limit=1).id,
                    "amount": (float(amount) / 100.0),
                    "date": datetime.today()
                }
            )

            api_secret = "AB563B8F4E9DB457F52E3D77F214C977"
            message = "vpc_AccessCode=E8AEDBAA"
            message += "&vpc_Amount=" + amount
            message += "&vpc_Command=pay"
            message += "&vpc_Currency=QAR"
            message += "&vpc_Locale=en"
            message += "&vpc_MerchTxnRef=txn1"
            message += "&vpc_Merchant=DB91363"
            message += "&vpc_OrderInfo=" + transaction.order_info
            message += "&vpc_ReturnURL=" + return_url
            message += "&vpc_Version=1"
            signature = hmac.new(binascii.unhexlify(bytes(api_secret, 'UTF-8')),
                                 msg=message.encode("UTF-8"),
                                 digestmod=hashlib.sha256).hexdigest().upper()

            return json.dumps({
                'status': "success",
                'data': {'key': signature,
                         'order_id': transaction.order_info,
                         'return_url': return_url
                         }
            })
        else:
            return json.dumps({'status': "error", 'msg': _("Token Error")})

    @http.route(['/my/payments/insert'], type='http', auth='user', website=True)
    def contact_payment_insert(self):

        request.env['ebs_mod.contact.payment'].create({
            'partner_id': request.env.user.partner_id.id,
            'amount': float(request.params['amount']),
            'currency_id': int(request.params['currency']),
            'desc': request.params['desc'],
        })
        return self.contact_payment_insert_form()


class CustomerPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['ticket_count'] = request.env['helpdesk.ticket'].search_count(
            [('partner_id', '=', request.env.user.partner_id.id)])
        if values.get('sales_user', False):
            values['title'] = _("Salesperson")
        return values

    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def my_helpdesk_tickets(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content',
                            **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        domain = [('partner_id', '=', user.partner_id.id)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Subject'), 'order': 'name'},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'id': {'input': 'id', 'label': _('Search ID')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # archive groups - Default Group By 'create_date'
        archive_groups = self._get_archive_groups('helpdesk.ticket', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            domain += search_domain

        # pager
        tickets_count = request.env['helpdesk.ticket'].search_count(domain)
        pager = portal_pager(
            url="/my/tickets",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=tickets_count,
            page=page,
            step=self._items_per_page
        )

        tickets = request.env['helpdesk.ticket'].search(domain, order=order, limit=self._items_per_page,
                                                        offset=pager['offset'])
        request.session['my_tickets_history'] = tickets.ids[:100]

        values.update({
            'date': date_begin,
            'tickets': tickets,
            'page_name': 'ticket',
            'default_url': '/my/tickets',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'sortby': sortby,
            'search_in': search_in,
            'search': search,
        })
        return request.render("helpdesk.portal_helpdesk_ticket", values)
