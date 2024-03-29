# -*- coding: utf-8 -*-
{
    'name': "QSheild Module",

    'summary': """
        This module contains custom modifications for QSsheild
        """,

    'description': """
       This module contains custom modifications for QSsheild
    """,

    'author': "Jaafar Khansa",
    'website': "http://www.ever-bs.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.3',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'contacts',
        'hr',
        'documents',
        'helpdesk',
    ],


    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'cron/document_cron_job.xml',
        'data/sequence.xml',
        'data/mail_template.xml',
        'views/views.xml',
        'views/templates.xml',
        'wizards/create_contact_document_wiz.xml',
        'wizards/message_wiz_view.xml',
        'wizards/change_sla_view.xml',
        'views/contacts_view_custom.xml',
        'views/contracts_view.xml',
        'views/contact_relation_type_view.xml',
        'views/document_custom.xml',
        'views/document_folder_custom.xml',
        'views/document_types_view.xml',
        'views/expense_types_view.xml',
        'views/service_types_view.xml',
        'views/service_request_view.xml',
        'views/tickets_view_custom.xml',
        'views/service_workflow_config_view.xml',
        'views/service_request_workflow_view.xml',
        'views/contact_payment_view.xml',
        'views/service_expenses_view.xml',
        'views/contact_payment_transaction_view.xml',
        'views/setting_view.xml',
        'views/excluded_company_view.xml',
        'views/menus.xml',
        'views/end_date_update_server_action.xml',
        # 'views/documents_assets.xml',
        'portal/contact_payment_portal.xml',
        'demo/demo.xml'
    ],
}


