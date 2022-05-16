# -*- coding: utf-8 -*-
{
    'name': "SaaS-Master:Tenant Database auto-backup",
    'summary': 'Automated Backups Of Tenant Dbs',
    'description': """
        The Tenant Database Auto-Backup module enables the user to make configurations for the automatic backup of the database. 
        Backups can be taken on the local system or on a remote server, through SFTP.
        You only have to specify the hostname, port, backup location and databasename (all will be pre-filled by default with correct data.
        If you want to write to an external server with SFTP you will need to provide the IP, username and password for the remote backups.
        The base of this module is 'auto_backup' module and then upgraded and heavily expanded.
        This module is made and provided by Yenthe Van Ginneken (Oocademy).
        Automatic backup for all such configured databases can then be scheduled as follows: 

        1) Go to Settings / Technical / Automation / Scheduled actions.
        2) Search the action 'Backup scheduler'.
        3) Set it active and choose how often you wish to take backups.
        4) If you want to write backups to a remote location you should fill in the SFTP details.
    """,
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    'website': "",
    'category': 'Saas',
    'version': '14.0.9',
    'license': 'OPL-1',
    "author": "Pragmatic Techsoft Pvt. Ltd.",
    'website': 'http://www.pragtech.co.in',

    # any module necessary for this one to work correctly
    'depends': ['base', 'saas_base', 'auto_backup', 'saas_product'],

    # always loaded
    'data': [
        'views/backup_view.xml',
        'template/templates.xml',
    ],
    'installable': True,
    'active': True,
}
