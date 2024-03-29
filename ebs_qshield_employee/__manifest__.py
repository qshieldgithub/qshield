# -*- coding: utf-8 -*-
{
    'name': "QShield Module",

    'summary': """
        This module contains custom modifications for QSshield Employee Module
        """,

    'description': """
       This module contains custom modifications for QSshield Employee Module
    """,

    'author': "Maria L Soliman",
    'website': "http://www.ever-bs.com/",
    'category': 'Uncategorized',
    'version': '0.4',
    'depends': ['base', 'contacts', 'hr', 'hr_contract', 'documents', 'helpdesk', 'ebs_qsheild_mod'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/res_country.xml',
        'views/employee_view_custom.xml',
        'views/contracts_view_custom.xml',
        'views/contacts_view_custom.xml',
        'views/visa_status.xml',
        'reports/employee_information_form.xml',
    ],
}
