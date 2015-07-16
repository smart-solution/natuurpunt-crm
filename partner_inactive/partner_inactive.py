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

from osv import osv, fields
from openerp.tools.translate import _



class partner_inactive(osv.osv):
	
	_name = 'partner.inactive'
	_description = 'Partner Inactive Reason'
	_columns = {
		'name': fields.char('Reason', size=256, required=True),
        'show_active_partner': fields.boolean('Show Active Partner'),
	}
partner_inactive()

class res_partner(osv.osv):

    _inherit = 'res.partner'
    _columns = {
        'inactive_id': fields.many2one('partner.inactive', 'Inactivity Reason'),
        'show_active_partner': fields.related('inactive_id', 'show_active_partner', type="boolean", string='Show Active Partner', readonly=True),
        'active_partner_id': fields.many2one('res.partner', 'Active Partner'),
    }

    def onchange_inactive(self, cr, uid, ids, inactive_id, context=None):
        print "IN on change"
        res = {}
        if inactive_id:
            inactive = self.pool.get('partner.inactive').browse(cr, uid, inactive_id)
            if inactive.show_active_partner:
                res['show_active_partner'] = True
            else:
                res['show_active_partner'] = False
        return {'value':res}




# SAMPLES

#class partner_inactive(osv.osv):
#	
#	_name = 'partner_inactive'
#	_description = 'partner_inactive'
#	_columns = {
#		'char': fields.char('char', size=64, required=True),
#		'integer': fields.integer('Integer'),
#		'float': fields.float('Float', digits=(16,2)),
#       'function': fields.function(_some_function, 
#       'related': fields.related(...
#	}
#partner_inactive()

#    _defaults = {
#            'state': 'draft',
#    {

#    def create(self, cr, uid, vals, context=None):
#        ...
#        return super(partner_inactive, self).create(cr, uid, vals, context=context)

#    def write(self, cr, uid, ids, vals, context=None):
#        ...
#        return super(partner_inactive, self).write(cr, uid, ids, vals, context=context)

#    def copy(self, cr, uid, id, default={}, context=None):
#        ...
#        return super(account_invoice, self).copy(cr, uid, id, default=default, context=context)


#       raise osv.except_osv(_('No product found !'), _('Could not find any product for the code %s'%(val))),

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
