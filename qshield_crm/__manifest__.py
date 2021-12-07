# -*- coding: utf-8 -*-
{
    'name': "Qshield CRM",

    'summary': """Custom CRM""",

    'description': """
        Customization in CRM
    """,

    'author': "Tech Ultra Solutions",
    'website': "http://www.techultrasolutions.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','sale_crm'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/qshiled_security_groups.xml',
        'data/ir_mail_activity.xml',
        'data/ir_cron_create_invoice.xml',
        'wizards/refuse_quotation_view.xml',
        'views/crm_lead_view.xml',
        'views/sale_order_view.xml',
        'views/sale_order_approver_settings_view.xml',

    ],
}
