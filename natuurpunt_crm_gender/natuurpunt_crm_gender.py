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
from openerp.tools.translate import _

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def onchange_title_gender(self, cr, uid, ids, title, gender, context=None):
        res = {}
        warning = ''
        if context and 'web' in context:
            web = True
        else:
            web = False
        if title:
            title_gender = None
            sql_stat = 'select gender from res_partner_title where id = %d' % (title, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                title_gender = sql_res['gender']

            if title_gender and gender and title_gender != gender:
                warning = "Het opgegeven geslacht komt niet overeen met het geslacht van de titel."
            
        if not (warning == '') and not web:
            warning_msg = { 
                    'title': _('Warning!'),
                    'message':_(warning)
            }
            return {'warning': warning_msg}
        return res

    def create(self, cr, uid, vals, context=None):
        if context and 'web' in context and 'title' in vals:
            gender = None
            sql_stat = 'select gender from res_partner_title where id = %d' % (vals['title'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                gender = sql_res['gender']
            if gender:
                vals['gender'] = gender

        res = super(res_partner, self).create(cr, uid, vals, context=context)

        return res

res_partner()


class res_partner_title(osv.osv):
    _inherit = 'res.partner.title'

    _columns = {
        'gender': fields.char('Geslacht', size=1)    
    }

res_partner_title()
