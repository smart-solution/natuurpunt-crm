# -*- coding: utf-8 -*-
##############################################################################
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
    "name" : "natuurpunt_crm_function",
    "version" : "1.0",
    "author" : "Natuurpunt (joeri.belis@natuurpunt.be)",
    "website" : "www.natuurpunt.be",
    "category" : "Membership",
    "description": """
    extend natuurpunt_crm function functionality 
    - fix name in res_organisation_function
    - check unique function
    - check if function is available for organisation structure
    - remove function tab on res_partner view when partner is organisation structure
""",
    "depends" : ["natuurpunt_crm",],
    "data" : ["natuurpunt_crm_function_view.xml",],
    "init_xml" : [],
    "update_xml" : [],
    "active": False,
    "installable": True
}
