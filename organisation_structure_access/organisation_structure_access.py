# -*- encoding: utf-8 -*-
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

from openerp.osv import fields, osv

class organisation_structure_access(osv.osv):
    _name = 'organisation.structure.access'
    _description = 'Organisation Structure Access'
    _columns = {
        'name': fields.char(string="name", size=100, required=True),
        'function_type_access': fields.one2many('function.type.access','organisation_structure_access_id','Access Function Type'),
        'organisation_type_access': fields.one2many('organisation.type.access','organisation_structure_access_id','Access Organisation Type'),
    }

organisation_structure_access()

class function_type_access(osv.osv):
    _name = 'function.type.access'
    _columns = {
        'organisation_structure_access_id': fields.many2one('organisation.structure.access', 'organisation structure access', required=True, ondelete='cascade', select=True, readonly=True),
        'function_type_id': fields.many2one('res.function.type', 'Function Type', select=True, ondelete='cascade'),
        'maintainable': fields.boolean('Maintainable'),
        'access': fields.boolean('Access'),
    }

function_type_access()

class organisation_type_access(osv.osv):
    _name = 'organisation.type.access'
    _columns = {
        'organisation_structure_access_id': fields.many2one('organisation.structure.access', 'organisation structure access', required=True, ondelete='cascade', select=True, readonly=True),
        'organisation_type_id': fields.many2one('res.organisation.type', 'Organisation Type', select=True, ondelete='cascade'),
    }

organisation_type_access()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
