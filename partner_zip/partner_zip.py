# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import re
from openerp.osv import fields, osv

class res_country_city(osv.osv):

	_name = 'res.country.city'
	
	_columns = {
		'name': fields.char('Name', size=128, required=True),
		'code': fields.integer('Code'),
		'zip': fields.char('Zipcode', size=24, select=True, required=True),
		'ref': fields.char('Ref', size=24, select=True),
		'country_id': fields.many2one('res.country', 'Country ID', required=True),
		'state_id': fields.many2one('res.country.state', 'State'),
		'street_ids': fields.one2many('res.country.city.street', 'city_id', 'Streets'),
		'lang_id': fields.many2one('res.lang','Lang'),
	}

	def name_get(self, cr, uid, ids, context=None):
		res = super(res_country_city, self).name_get(cr, uid, ids, context=context)
		res2 = []
		for r in res:
			city = self.browse(cr, uid, r[0])
			res2.append((r[0],city.name + ' (' + city.zip + ')'))
		return res2

        def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
            if not args:
                args = []
            ids = self.search(cr, user, [('zip', operator, name)]+ args, limit=limit, context=context)
            ids += self.search(cr, user, [('name', operator, name)]+ args, limit=limit, context=context)
            return self.name_get(cr, user, ids, context)

	_order = 'name'
		
res_country_city()

class res_country_city_street(osv.osv):

	_name = 'res.country.city.street'
	
	_columns = {
		'name': fields.char('Name', size=128, required=True),
		'code': fields.integer('Code'),
		'city_id': fields.many2one('res.country.city', 'City', required=True),
		'country_id': fields.related('city_id', 'country_id', type='many2one', 
			relation='res.country', store=True, string='Country ID', readonly=True),
		'zip': fields.related('city_id', 'zip', type='char', store=True, string='Zip', readonly=True),
	}

	_order = 'name'

res_country_city_street()



