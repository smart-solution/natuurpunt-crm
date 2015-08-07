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

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

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

res_partner()

class res_organisation_function(osv.osv):    
    _name = 'res.organisation.function'
    _inherit = 'res.organisation.function'

    def _check_unique_type(self, cr, uid, vals, context=None):
        function_type_obj = self.pool.get('res.function.type')
        unique_type = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['unique_type'], context=context)['unique_type']
        if unique_type and 'partner_id' in vals and vals['partner_id']:
            ids = self.search(cr, uid, [('partner_id', '=', vals['partner_id']),('function_type_id', '=', vals['function_type_id'])])
            if ids:
                res_partner_obj = self.pool.get('res.partner')
                partner_name = res_partner_obj.read(cr, uid, vals['partner_id'], fields=['name'],context=context)['name']
                raise osv.except_osv(_('Error!'), _('Function %s already exists for %s\nThis is an unique function'%(vals['name'],partner_name)))
            else:
                return True
        else: 
            return True
        
    def _check_organisation_type_ids(self, cr, uid, vals, context=None):
        function_type_obj = self.pool.get('res.function.type')        
        organisation_type_ids = function_type_obj.read(cr, uid, vals['function_type_id'], fields=['organisation_type_ids'], context=context)['organisation_type_ids']
        if organisation_type_ids and 'partner_id' in vals and vals['partner_id']:
            res_partner_obj = self.pool.get('res.partner')
            organisation_type_id = res_partner_obj.read(cr, uid, vals['partner_id'], fields=['organisation_type_id'], context=context)['organisation_type_id']
            if not organisation_type_id[0] in organisation_type_ids:
                res_partner_obj = self.pool.get('res.partner')
                partner_name = res_partner_obj.read(cr, uid, vals['partner_id'], fields=['name'],context=context)['name']
                raise osv.except_osv(_('Error!'), _('Function %s is not available for %s'%(vals['name'],partner_name)))
            else:
                return True
        else:
            return True        
        
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

res_organisation_function()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: