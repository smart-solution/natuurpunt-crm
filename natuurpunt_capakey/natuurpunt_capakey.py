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

from openerp.osv import fields, osv
from natuurpunt_tools import sql_wrapper

depth_tree = 7

class res_partner(osv.osv):
        _name = 'res.partner'
        _inherit = 'res.partner'

        def search_capakey(self, cr, uid, query, context=None):
            if context is None:
                context = {}
            res = []
            try:
                sql_res = sql_wrapper(query)(cr)
            except:
                return res
            else:
                if len(sql_res) == 1 and sql_res[0]['level'] > 0 :
                    if abs(sql_res[0]['level'] - depth_tree) == sql_res[0]['children']:
                        try:
                            name = sql_res[0]['name']
                            query = "select name from fdw_capakey where lft > {} AND rgh < {} AND level = {}"
                            sql_res = sql_wrapper(query.format(sql_res[0]['lft'],sql_res[0]['rgh'],7))(cr)
                        except:
                            return res
                        else:
                            sql_func = lambda v: {name:v['name']}
                    else:
                        sql_func = lambda v: {v['name']:[v['lft'], v['rgh']]}
                else:
                    sql_func = lambda v: {v['name']:[v['lft'], v['rgh']]}
                return map(sql_func ,sql_res)

        def view_capakey_builder(self, cr, uid, ids, context=None):
            ir_model_data = self.pool.get('ir.model.data')
            try:
               form_id = ir_model_data.get_object_reference(cr, uid, 'natuurpunt_capakey', 'natuurpunt_capakey_form')[1]
            except ValueError:
               form_id = False
            return {
                'type': 'ir.actions.act_window',
                'name': 'Capakey builder',
                'view_mode': 'form',
                'view_type': 'form',
                'views': [(form_id, 'form')],
                'view_id': form_id,
                'res_model': 'memory.capakey.builder',
                'target': 'new',
                'context': context,
            }

res_partner()

class memory_capakey_builder(osv.TransientModel):
    _name = 'memory.capakey.builder'

    _columns = {
        'capakey' : fields.char('capakey'),
    }

    def capakey_build(self, cr, uid, ids, context=None):
        capakey = self.browse(cr, uid, ids)[0]
        context['capakey'] = capakey.capakey
        return {'type': 'ir_actions_act_close_wizard_and_reload_capakey',
                'context': context
        }

