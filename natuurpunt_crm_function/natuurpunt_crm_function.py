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
from string import Template
from tools.translate import _
from openerp import SUPERUSER_ID
import datetime
from natuurpunt_tools import sql_wrapper
import itertools
from operator import itemgetter
from collections import Counter

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _check_org_function_parent_ids(self, cr, uid, ids, context=None):
        for partner in self.browse(cr,uid,ids):
            self.validate_functions(cr,uid,partner)
        return True

    _constraints = [
        (_check_org_function_parent_ids, 'Error validate_functions', ['organisation_function_parent_ids'])
    ]

    def count_members(self,cr,uid,partner_id,context=None):
        sql_stat = """
            SELECT count(res_partner."id")
            FROM "res_partner" res_partner
            left join res_partner_address_state on res_partner.address_state_id = res_partner_address_state.Id
            WHERE
            (res_partner."membership_state" = 'paid' 
             or res_partner."membership_state" = 'invoiced' 
             or res_partner."free_member" IS TRUE )
             AND (res_partner.address_state_id <> 2 or res_partner.address_state_id is null)
             AND res_partner.active = true
             AND res_partner.no_department IS NOT TRUE
             AND ((res_partner.department_choice_id IS null and res_partner.department_id = %s )
             or res_partner.department_choice_id = %s);
             """
        sql_res = sql_wrapper(sql_stat%(partner_id,partner_id))(cr)
        return sql_res[0]['count']

    def occurance(self,cr,uid,partner,context=None):
        res = 1
        organisation_type_id = 3
        domain =  [
            ('partner_up_id', '=', partner.id),
            ('organisation_type_id','=',organisation_type_id),
        ]
        ids_kern = self.search(cr,uid,domain)
        count_members = self.count_members(cr,uid,partner.id)
        if count_members > 750:
            res = res + ((count_members - 750)-1)/250+1
        res = res + len(ids_kern)
        return res

    def validate_functions(self,cr,uid,partner,context=None):
        today = datetime.datetime.today().strftime('%Y-%m-%d')
        rof_obj = self.pool.get('res.organisation.function')

        # validatie van contant ipv geleding
        if not (partner.organisation_type_id):
            domain = [
                ('person_id', '=', partner.id),
                 '&','|',('valid_from_date', '=', False), ('valid_from_date', '<=', today),
                 '|',('valid_to_date', '=', False), ('valid_to_date', '>=', today),
            ]
            ids = rof_obj.search(cr,uid,domain)        
            if ids:
                partner_ids = list(set(map(lambda rof: rof.partner_id.id, rof_obj.browse(cr,uid,ids))))
                for p in self.browse(cr,uid,partner_ids):
                    self.validate_functions(cr,uid,p,context=context)
            return True 
        else:
            domain = [
                ('partner_id', '=', partner.id),
                 '&','|',('valid_from_date', '=', False), ('valid_from_date', '<=', today),
                 '|',('valid_to_date', '=', False), ('valid_to_date', '>=', today),
            ]

        organisation_type_id = partner.organisation_type_id.id
        res_function_dependency_obj = self.pool.get('res.function.dependency')
        categ_ids = [niche.categ_id.id for niche in partner.niche_ids]
        dep_func_domain =  [
            ('organisation_type_id','=',organisation_type_id),
            ('regional_level','=',partner.regional_level),            
        ]
        if categ_ids:
            dep_func_domain.append(('categ_id','in',categ_ids))
        res_function_dependency_ids = res_function_dependency_obj.search(cr,uid,dep_func_domain)
        if res_function_dependency_ids:
            dependencies = []
            dependency_functions = []
            for dep in res_function_dependency_obj.browse(cr,uid,res_function_dependency_ids):
                func1_id = dep.function_type_id.id
                func2_id = dep.depends_on_function_type_id.id
                # functional occurance
                if dep.occurance:
                    dependencies.append( (func1_id, func2_id, dep.occurance) )
                else:
                    dependencies.append( (func1_id, func2_id, self.occurance(cr,uid,partner) ) )
                dependency_functions.append(func1_id)
                dependency_functions.append(func2_id)
            dependencies = sorted(dependencies,key=lambda x: x[1],reverse=True)
            dep_matrix_domain = list(domain) #deep copy
            dep_matrix_domain.append(('function_type_id', 'in', dependency_functions))
            ids = rof_obj.search(cr,uid,dep_matrix_domain)
            dependency_matrix = map(lambda rof: (rof.function_type_id.id, rof.person_id.id), rof_obj.browse(cr,uid,ids) )

            def process_dependency_matrix():
                sorter = sorted(dependency_matrix, key=itemgetter(1))
                grouper = itertools.groupby(sorter, key=itemgetter(1))
                d = {k: list(map(itemgetter(0), v)) for k, v in grouper}
                res = []
                for person_id, function_ids in d.items():
                    dependencies_match = []
                    for dep in dependencies:
                        if dep[1]:
                            if dep[0] in function_ids and dep[1] in function_ids:
                                function_ids.remove(dep[0])
                                function_ids.remove(dep[1])
                                dependencies_match.append( (dep[0],dep[1]) )
                        else:
                            if dep[0] in function_ids:
                                function_ids.remove(dep[0])
                                dependencies_match.append( (dep[0], False) )
                    res.append((person_id,dependencies_match,function_ids))
                return res

            def validate_occurances():
                deps = map(lambda t: t[1], dependency_rofs)
                deps_list = list(itertools.chain.from_iterable(deps))
                counter = Counter(tup for tup in deps_list)
                for dep in dependencies:
                    count_occurance = counter[(dep[0],dep[1])]
                    if count_occurance > dep[2]:
                        rft = self.pool.get('res.function.type').browse(cr,uid,dep[0])
                        from_function_name = rft.name
                        if dep[1]:
                            rft = self.pool.get('res.function.type').browse(cr,uid,dep[1])
                            to_function_name = rft.name
                            mess = _('%s:\n\nFunction %s depending on %s\ncan only have %s cccurances')
                            raise osv.except_osv(_('Error!'), mess%(partner.name,from_function_name,to_function_name,dep[2]))
                        else:
                            mess = _('%s:\n\nFunction %s\ncan only have %s cccurances')
                            raise osv.except_osv(_('Error!'), mess%(partner.name,from_function_name,dep[2]))

            if dependency_matrix:
                dependency_rofs = process_dependency_matrix()
                validate_occurances()
                for person_rofs in dependency_rofs:
                    if person_rofs[2]:
                        func = person_rofs[2][0]
                        rft = self.pool.get('res.function.type').browse(cr,uid,func)
                        function_name = rft.name
                        person = self.pool.get('res.partner').browse(cr,uid,person_rofs[0])
                        pe = '[{}] {}'.format(person.id,person.name)
                        pa = '[{}] {}'.format(partner.id,partner.name)
                        mess = _('%s:\n\nFunction %s\nhas missing dependency\nfor %s')
                        raise osv.except_osv(_('Error!'), mess%(pa,function_name,pe))
        else:
            dependency_functions = []
            
        ids = rof_obj.search(cr,uid,domain)
        if ids:
            function_type_ids = map(lambda rof: rof.function_type_id.id, rof_obj.browse(cr,uid,ids))
            allowed_functions_type_ids = map(lambda rft: rft.id,partner.organisation_type_id.function_type_ids)
            allowed_functions_type_ids = allowed_functions_type_ids + dependency_functions
            for function_type_id in filter(lambda x:x not in allowed_functions_type_ids,function_type_ids):
                rft = self.pool.get('res.function.type').browse(cr,uid,function_type_id)
                function_name = rft.name
                raise osv.except_osv(_('Error!'), _('%s:\n\nFunction %s is not available for %s'%(partner.name,function_name,partner.name)))

    def _replace_init_name(self, cr, uid, organisation_function_child_ids, context=None):
        """
        loop the list of operations that makes the o2m value and reformat name field
        """
        for item in organisation_function_child_ids:
            if len(item) == 3 and item[2] and 'function_type_id' in item[2]:
                function_type_obj = self.pool.get('res.function.type').browse(cr,uid,item[2]['function_type_id'])
                #reformat name
                item[2]['name'] = function_type_obj.name
            yield item

    def onchange_organisation_function_child_ids(self, cr, uid, ids, organisation_function_child_ids, context=None):
        res = {}
        new_organisation_function_child_ids = list(self._replace_init_name(cr,uid,organisation_function_child_ids,context=context))
        res['value'] = {}
        res['value']['organisation_function_child_ids'] = new_organisation_function_child_ids
        return res
    
    def write(self, cr, uid, ids, vals, context=None):        
        res = super(res_partner, self).write(cr, uid, ids, vals, context=context)
        # sync active state of partner / person with organisation function        
        if 'active' in vals :
            res_org_fnc_obj = self.pool.get('res.organisation.function')
            domain = ['|',('partner_id', 'in', ids),('person_id', 'in', ids)]            
            if vals['active']:
                domain.append(('active','=',False))
            res_org_fnc_ids = res_org_fnc_obj.search(cr, SUPERUSER_ID, domain)
            for res_org_fnc in res_org_fnc_obj.browse(cr, SUPERUSER_ID, res_org_fnc_ids):            
                active = (res_org_fnc.partner_id.active if res_org_fnc.partner_id else True) and (res_org_fnc.person_id.active if res_org_fnc.person_id else True) 
                res_org_fnc_obj.sync_active(cr, SUPERUSER_ID, [res_org_fnc.id], active, context=context)
        return res

res_partner()

class res_organisation_function(osv.osv):    
    _name = 'res.organisation.function'
    _inherit = 'res.organisation.function'

    def _check_unique_type(self, cr, uid, vals, context=None):
        res_partner_obj = self.pool.get('res.partner')
        function_type_obj = self.pool.get('res.function.type')
        unique_type = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['unique_type'], context=context)['unique_type']
        if unique_type and 'partner_id' in vals and vals['partner_id']:
            ids = self.search(cr, uid, [('partner_id', '=', vals['partner_id']),('function_type_id', '=', vals['function_type_id'])])
            if ids:
                if self.browse(cr,uid,ids)[0].person_id.id != vals['person_id']:
                    partner_name = res_partner_obj.read(cr, uid, vals['partner_id'], fields=['name'],context=context)['name']
                    function_name = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['name'], context=context)['name']
                    raise osv.except_osv(_('Error!'), _('Function %s already exists for %s\nThis is an unique function'%(function_name,partner_name)))
                else:
                    res = True
            else:
                res = True
        else: 
            res = True
        unique_for_person = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['unique_for_person'], context=context)['unique_for_person']
        if unique_for_person and 'person_id' in vals and vals['person_id']:
            partner = res_partner_obj.browse(cr, uid, vals['partner_id'],context=context)       
            domain = [
                ('person_id', '=', vals['person_id']),
                ('function_type_id', '=', vals['function_type_id']),
                ('partner_id.organisation_type_id','=',partner.organisation_type_id.id),
            ]
            ids = self.search(cr,uid,domain)
            if ids:
                if len(ids):
                    person_name = res_partner_obj.read(cr, uid, vals['person_id'], fields=['name'],context=context)['name']
                    function_name = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['name'], context=context)['name']
                    raise osv.except_osv(_('Error!'), _('Function %s already exists for %s\nThis is an unique function'%(function_name,person_name)))
                else:
                    res = True   
            else: 
                res = True
        else:
            res = True
        return res
        
    def _check_organisation_type_ids(self, cr, uid, vals, context=None):
        pass
        """
        function_type_obj = self.pool.get('res.function.type')        
        organisation_type_ids = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['organisation_type_ids'], context=context)['organisation_type_ids']
        if organisation_type_ids and 'partner_id' in vals and vals['partner_id']:
            res_partner_obj = self.pool.get('res.partner')
            organisation_type_id = res_partner_obj.read(cr, uid, vals['partner_id'], fields=['organisation_type_id'], context=context)['organisation_type_id']
            if not organisation_type_id[0] in organisation_type_ids:
                res_partner_obj = self.pool.get('res.partner')
                partner_name = res_partner_obj.read(cr, uid, vals['partner_id'], fields=['name'],context=context)['name']
                function_name = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['name'], context=context)['name']
                raise osv.except_osv(_('Error!'), _('Function %s is not available for %s'%(function_name,partner_name)))
            else:
                return True
        else:
            return True        
        """ 
        
    def onchange_organisation_function_id(self, cr, uid, ids, function_type_id, context=None):
        #The result will be stored in a dictionary  
        res = {}  
        #Now you can change other fields with the updated values passed as parameters
        function_type_obj = self.pool.get('res.function.type')  
        res['name'] = function_type_obj.read(cr, uid, function_type_id, fields=['name'], context=context)['name']
        return {'value': res}
    
    def create(self, cr, uid, vals, context=None):        
        self._check_unique_type(cr, uid, vals=vals, context=context)
        self._check_organisation_type_ids(cr, uid, vals=vals, context=context)            
        return super(res_organisation_function, self).create(cr, uid, vals=vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):        
        for rof in self.browse(cr, uid, ids, context):
            if not 'partner_id' in vals:
                vals['partner_id'] = rof.partner_id.id
            if not 'function_type_id' in vals:
                vals['function_type_id'] = rof.function_type_id.id
            if not 'person_id' in vals:
                vals['person_id'] = rof.person_id.id        
        self._check_unique_type(cr, uid, vals=vals, context=context)
        self._check_organisation_type_ids(cr, uid, vals=vals, context=context)        
        return super(res_organisation_function, self).write(cr, uid, ids, vals=vals, context=context)

    def sync_active(self, cr, uid, ids, active, context=None):
        vals = {'active':active}
        return super(res_organisation_function, self).write(cr, uid, ids, vals=vals, context=context)

    def get_partners(self, cr, uid, ids, context=None):
        sql_stat = """
        select
        p1.id as person_id, 
        p1.name as person_name, 
        p2.id as partner_id, 
        p2.name as partner_name,
        t.company_id as vzw_id,
        c.name as vzw_id,
        t.name as stem_name
        from res_organisation_function as f
        join res_partner p1 on p1.id = f.person_id
        join res_partner p2 on p2.id = f.partner_id
        join res_function_type as t on t.id = f.function_type_id
        join res_company as c on c.id = t.company_id
        where (f.valid_from_date is null or f.valid_from_date <= now())
          and (f.valid_to_date is null or f.valid_to_date >= now())
          and t.company_id is not null
          and f.active
        order by t.company_id;
        """
        sql_res = sql_wrapper(sql_stat)(cr)
        return sql_res
    
    _columns = {
        'active': fields.boolean('Active'),
    }
    
    _defaults = {       
        'active' : True,
    }

res_organisation_function()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
