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

from osv import osv, fields
from tools.translate import _
import logging

_logger = logging.getLogger(__name__)

def organisation_structure_access(self,cr,uid,name):
    osa_obj = self.pool.get('organisation.structure.access')
    ids = osa_obj.search(cr,uid,[('name','=',name)])
    for osa in osa_obj.browse(cr,uid,ids):
        yield osa

def function_type_access(self,cr,uid,context=None):
    maintainable = {}
    access = {}
    context = context or {}
    for osa in organisation_structure_access(self,cr,uid,context['organisation_structure_access']):
        function_type_access = osa.function_type_access
        map(lambda i: maintainable.setdefault(i.function_type_id.id,i.maintainable),function_type_access)
        map(lambda i: access.setdefault(i.function_type_id.id,i.access),function_type_access)
    return maintainable, access

def organisation_type_access(self,cr,uid,context=None):
    context = context or {}
    for osa in organisation_structure_access(self,cr,uid,context['organisation_structure_access']):
        return map(lambda i: i.organisation_type_id.id, osa.organisation_type_access)
    return []

class res_organisation_function(osv.osv):
    _name = 'res.organisation.function'
    _inherit = 'res.organisation.function'

    def rest_get_organisations(self,cr,uid,ids,context=None):
        res = []

        domain = [('person_id','in',ids)]
        if 'organisation_structure_access' in context:
            m, access = function_type_access(self,cr,uid,context=context)
            osa_function_type_ids = [k for k,v in access.items() if v]
            domain.append( ('function_type_id','in',osa_function_type_ids) )
        else:
            access = {}

        rof_ids = self.search(cr,uid,domain)
        if rof_ids:
            for rof in self.browse(cr,uid,rof_ids,context=context):
                d = {
                    'id': rof.partner_id.id,
                    'name': rof.partner_id.name,
                    'regional_level': rof.partner_id.regional_level,
                    'organisation_type_id': rof.partner_id.organisation_type_id.id,
                }
                res.append(d)

        return res

    def rest_get_functions(self,cr,uid,ids,context=None):
        res = []

        domain = [('partner_id','in',ids)]
        if 'organisation_structure_access' in context:
            maintainable, a = function_type_access(self,cr,uid,context=context)
            osa_function_type_ids = [k for k,v in maintainable.items()]
            domain.append( ('function_type_id','in',osa_function_type_ids) )
        else:
            maintainable = {}

        rof_ids = self.search(cr,uid,domain)
        if rof_ids:
            for rof in self.browse(cr,uid,rof_ids,context=context):
                function_type_id = rof.function_type_id.id
                d = {
                    'id': rof.id,
                    'maintainable': maintainable[function_type_id] if function_type_id in maintainable else True,
                    'person': {
                        'id': rof.person_id.id,
                        'name': rof.person_id.name,
                    },
                    'function': {
                        'id': function_type_id,
                        'name': rof.function_type_id.name,
                    },
                }
                res.append(d)
        return res

res_organisation_function()

class res_organisation_type(osv.osv):        
    _name = 'res.organisation.type'
    _inherit = 'res.organisation.type'

    def rest_get_functions_organisations(self,cr,uid,ids,context=None):
        res = []

        if 'organisation_structure_access' in context:
            m, access = function_type_access(self,cr,uid,context=context)
            function_visible = lambda x: x in [k for k,v in access.items()]
        else:
            function_visible = lambda x: True

        for rot in self.browse(cr,uid,ids,context=context):
            for func in rot.function_type_ids:
                d = { 'id': func.id, 'name': func.name }
                if d not in res and function_visible(d['id']):
                    res.append(d)
            for func in rot.function_dependency_ids:
                d = { 'id': func.function_type_id.id, 'name': func.function_type_id.name }
                if d not in res and function_visible(d['id']):
                    res.append(d)
        return res

res_organisation_type()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
