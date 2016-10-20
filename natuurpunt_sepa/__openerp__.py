# -*- coding: utf-8 -*-
##############################################################################
#
#    Smart Solution bvba
#    Copyright (C) 2010-Today Smart Solution BVBA (<http://www.smartsolution.be>).
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
    "name" : "natuurpunt_sepa",
    "version" : "1.0",
    "author" : "Smart Solution (wim.audenaert@smartsolution.be)",
    "website" : "www.smartsolution.be",
    "category" : "Generic Modules/Base",
    "description": """
""",
    "depends" : ["account_banking_sepa_direct_debit","natuurpunt_membership","natuurpunt_account","multi_analytical_account","account_voucher"],
    "init_xml" : [
        ],
    "update_xml" : [
        'natuurpunt_sepa_view.xml',
        ],
    "active": False,
    "installable": True
}
