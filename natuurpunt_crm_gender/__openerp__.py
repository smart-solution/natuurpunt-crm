# -*- coding: utf-8 -*-
##############################################################################
#
#    Natuurpunt VZW
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
    'name': 'natuurpunt_crm_gender',
    'version': '1.0',
    'category': 'CRM',
    'summary': 'CRM Gender module',
    'description': """
    extend natuurpunt_crm gender functionality 
        - prevent title and gender discrepancies
        - if title is selected and no gender, try to set the gender
    """,
    'author': 'Natuurpunt (willem.liebens@natuurpunt.be)',
    'website': 'http://www.natuurpunt.be',
    'depends': ['natuurpunt_crm'],
    'data': [
	'natuurpunt_crm_gender_view.xml'
    ],
   'installable': True,
}