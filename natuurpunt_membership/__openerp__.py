# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Natuurpunt Membership',
    'version': '1.0',
    'category': 'Membership',
    'description': """
    Natuurpunt
    """,
    'author': 'Smart Solution',
    'website': 'http://www.smartsolution.be',
    'depends': ['membership','natuurpunt_crm','natuurpunt_account'],
    'data': [
	    'natuurpunt_membership_view.xml',
        'natuurpunt_membership_workflow.xml',
        'security/natuurpunt_membership_security.xml',
        'security/ir.model.access.csv',
    ],
   'installable': True,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
