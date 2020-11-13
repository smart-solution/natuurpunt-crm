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

def res_organisation_type(self,cr,uid,organisation_type_id):
    rot_obj = self.pool.get('res.organisation.type')
    ids = rot_obj.search(cr,uid,[('id','=',organisation_type_id)])
    for rot in rot_obj.browse(cr,uid,ids):
        for func in rot.function_type_ids:
            yield func

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

    def deps_to_partner_deps(self,cr,uid,partner_id,dependencies,partner_ids=None,split_filter=lambda i: i[1]):
        deps = filter(split_filter,dependencies)
        functions_type_ids = map(lambda i: i[0],deps)
        domain = [('partner_id','in',[partner_id]),('function_type_id','in',functions_type_ids)]
        rof_ids = self.search(cr,uid,domain)
        res = self.browse(cr,uid,rof_ids)
        if len(deps) == len(dependencies):
            return res
        if partner_ids is None:
            partner_ids = map(lambda rof: rof.person_id.id,res)
            return res + self.deps_to_partner_deps(cr,uid,partner_id,dependencies,partner_ids,split_filter=lambda i: not i[1])
        else:
            return filter(lambda rof: rof.person_id.id not in partner_ids,res)

    def rest_get_person_afdeling(self,cr,uid,ids,membership_nbr,context=None):
        res = []

        person_domain = [
            ('membership_nbr','=',membership_nbr),
            ('iets_te_verbergen','=',False),
            '|',('department_id','in',ids),('department_choice_id','in',ids),]       
        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                person_ids = partner_obj.search(cr,uid,person_domain)
                for person in partner_obj.browse(cr,uid,person_ids):
                    mline, membership_state = partner_obj._np_membership_state(cr, uid, person, context=context)
                    if membership_state in ['paid','invoiced','free','wait_member']:
                        res.append({'id':person.id,'name':person.name,})
            except ValueError:
                pass
        return res

    def rest_get_person_werkgroep(self,cr,uid,ids,membership_nbr,context=None):
        res = []

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                person_domain = filter(None,[
                    ('membership_nbr','=',membership_nbr),
                    ('iets_te_verbergen','=',False),
                    ('state_id','=',partner.state_id.id) if partner.regional_level == 'P' else False,
                    ('zip_id','in',map(lambda i:i.id,partner.m2m_zip_ids)) if partner.regional_level in ['L','R'] else False,
                ]) 
                person_ids = partner_obj.search(cr,uid,person_domain)
                for person in partner_obj.browse(cr,uid,person_ids):
                    mline, membership_state = partner_obj._np_membership_state(cr, uid, person, context=context)
                    if membership_state in ['paid','invoiced','free','wait_member']:
                        res.append({'id':person.id,'name':person.name,})
            except ValueError:
                pass
        return res        

    def rest_list_cities(self,cr,uid,context=None):
        res = []
        res_country_city_obj = self.pool.get('res.country.city')
        ids = res_country_city_obj.search(cr,uid,[])
        for city in res_country_city_obj.browse(cr,uid,ids):
            res.append({'id':city.id,'name':city.name,'zip':city.zip,})
        return res

    def rest_list_states(self,cr,uid,context=None):
        res = []
        res_country_state_obj = self.pool.get('res.country.state')
        ids = res_country_state_obj.search(cr,uid,[('country_id','=',21)])
        for state in res_country_state_obj.browse(cr,uid,ids):
            res.append({'id':state.id,'name':state.name,})
        return res        

    def rest_get_cities(self,cr,uid,ids,context=None):
        res = []

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                for city in partner.m2m_zip_ids:
                    res.append({'id':city.id,'name':city.name,'zip':city.zip,})
            except ValueError:
                pass
        return res

    def rest_get_states(self,cr,uid,ids,context=None):
        res = []

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                if partner.state_id:
                    res.append({'id':partner.state_id.id,'name':partner.state_id.name,})
                else:
                    res.append({'id':False,'name':'',})
            except ValueError:
                pass
        return res

    def rest_unlink_cities(self,cr,uid,ids,city_id,context=None):
        res = False

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                res = partner_obj.write(cr,uid,[partner_id],{'m2m_zip_ids':[(3,city_id)]})
            except ValueError:
                pass
        return res

    def rest_unlink_states(self,cr,uid,ids,context=None):
        res = False

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                res = partner_obj.write(cr,uid,[partner_id],{'state_id':False})
            except ValueError:
                pass
        return res

    def rest_post_cities(self,cr,uid,ids,city_id,context=None):
        res = False

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                res = partner_obj.write(cr,uid,[partner_id],{'m2m_zip_ids':[(4,city_id)]})
            except ValueError:
                pass
        return res

    def rest_post_states(self,cr,uid,ids,state_id,context=None):
        res = False

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                res = partner_obj.write(cr,uid,[partner_id],{'state_id':state_id})
            except ValueError:
                pass
        return res

    def rest_list_niches(self,cr,uid,context=None):
        res = []
        res_niche_obj = self.pool.get('res.niche')
        ids = res_niche_obj.search(cr,uid,[])
        for niche in res_niche_obj.browse(cr,uid,ids):
            res.append({'id':niche.id,'name':niche.name,})
        return res

    def rest_get_niches(self,cr,uid,ids,context=None):
        res = []

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                for niche in partner.niche_ids:
                    res.append({'id':niche.id,'name':niche.name,})
            except ValueError:
                pass
        return res

    def rest_unlink_niches(self,cr,uid,ids,niche_id,context=None):
        res = False

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                res = partner_obj.write(cr,uid,[partner_id],{'niche_ids':[(3,niche_id)]})
            except ValueError:
                pass
        return res

    def rest_post_niches(self,cr,uid,ids,niche_id,context=None):
        res = False

        domain = [('partner_id','in',ids)]
        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                res = partner_obj.write(cr,uid,[partner_id],{'niche_ids':[(4,niche_id)]})
            except ValueError:
                pass
        return res        

    def rest_get_organisations(self,cr,uid,ids,context=None):
        res = []

        domain = [('person_id','in',ids)]
        if 'organisation_structure_access' in context:
            m, access = function_type_access(self,cr,uid,context=context)
            osa_function_type_ids = [k for k,v in access.items() if v]
            osa_organisation_type_ids = organisation_type_access(self,cr,uid,context=context)
            domain.append( ('function_type_id','in',osa_function_type_ids) )
            domain.append( ('partner_id.organisation_type_id','in',osa_organisation_type_ids) )

        rof_ids = self.search(cr,uid,domain)
        if rof_ids:
            for rof in self.browse(cr,uid,rof_ids,context=context):
                d = {
                    'id': rof.partner_id.id,
                    'name': rof.partner_id.name,
                    'regional_level': rof.partner_id.regional_level,
                }
                if d not in res:
                    res.append(d)
        return res

    def rest_get_functions_assigned(self,cr,uid,ids,context=None):
        res = []

        def rof_to_dict():
            return {
                'id': rof.id,
                'maintainable': is_maintainable(rof.function_type_id.id),
                'valid_from_date': rof.valid_from_date,
                'valid_to_date': rof.valid_to_date,
                'person': {
                    'id': rof.person_id.id,
                    'name': rof.person_id.name,
                },
                'function': {
                    'id': rof.function_type_id.id,
                    'name': rof.function_type_id.name,
                },
            }

        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try:
                partner_id = partner.id
                dependencies, dependency_functions = partner_obj.partner_dependencies(cr,uid,partner)
                domain = [('partner_id','in',[partner_id])]

                if 'organisation_structure_access' in context:
                    maintainable, a = function_type_access(self,cr,uid,context=context)
                    osa_function_type_ids = [k for k,v in maintainable.items()]
                    domain.append( 
                        ('function_type_id',
                         'in',
                         filter(lambda i: i not in dependency_functions,osa_function_type_ids))
                    )
                    is_maintainable = lambda x: maintainable[x]
                else:
                    if dependency_functions:
                        domain.append(
                            ('function_type_id',
                             'not in',
                             filter(None,dependency_functions))
                        )
                    is_maintainable = lambda x: True

                rof_ids = self.search(cr,uid,domain)
                for rof in self.browse(cr,uid,rof_ids,context=context):
                    res.append(rof_to_dict())
                for rof in self.deps_to_partner_deps(cr,uid,partner_id,dependencies):
                    try:
                        res.append(rof_to_dict())
                    except KeyError:
                        pass
            except ValueError:
                pass
        return res

    def rest_get_functions_all(self,cr,uid,ids,context=None):
        res = []

        if 'organisation_structure_access' in context:
            maintainable, access = function_type_access(self,cr,uid,context=context)
            is_maintainable = lambda x: x in [k for k,v in maintainable.items()]
        else:
            is_maintainable = lambda x: True

        partner_obj = self.pool.get('res.partner')
        for partner in partner_obj.browse(cr,uid,ids):
            try: 
                partner_id = partner.id
                dependencies, dependency_functions = partner_obj.partner_dependencies(cr,uid,partner)
                partner_deps = self.deps_to_partner_deps(cr,uid,partner_id,dependencies)
                counter_deps = map(lambda rof: rof.function_type_id.id,partner_deps)
                for func in dependencies:
                    d = {
                        'id': func[0],
                        'name': func[3].name,
                        'occurance': (counter_deps.count(func[0]),func[2]),
                    }
                    if is_maintainable(d['id']):
                        res.append(d)
                for func in res_organisation_type(self,cr,uid,partner.organisation_type_id.id):
                    d = { 'id': func.id, 'name': func.name }
                    if is_maintainable(d['id']):
                        res.append(d)
            except ValueError:
                pass
        return res 

    def rest_put_functions(self,cr,uid,ids,vals,context=None):
        return self.write_res_organisation_function(cr,uid,ids,vals)

    def rest_post_functions(self,cr,uid,vals,context=None):
        context = context or {}        
        try:
            context['validate'] = True
            partner_id = self.pool.get('res.partner').create_org_function_parent_ids(cr,uid,vals,context)
            res = self.rest_get_functions_assigned(cr,uid,[partner_id],context)
        except Exception as err:
            return (False, str(err))
        return (True, res)

    def rest_unlink_functions(self,cr,uid,ids,context=None):
        return self.unlink_res_organisation_function(cr,uid,ids)
       
res_organisation_function()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
