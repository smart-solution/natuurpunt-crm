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

class web_report_download(osv.osv):
        _name = 'web.report.download'

        _columns = {
                'name': fields.char('report download', size=128, required=True),
                'web_report_id': fields.many2one('web.report', 'Rapport', select=True, ondelete='cascade'),                
                'res_organisation_function_id': fields.many2one('res.organisation.function', 'Organisatie functie', select=True, ondelete='cascade'),
		        'param': fields.char('param', size=128, required=True),
                'format': fields.char('format', size=5, required=True),
        }
        
        _defaults = {
                'format': 'XLS'
        }        

web_report_download()

class web_report(osv.osv):
        _name = 'web.report'

        _columns = {
                'name': fields.char('name', size=128, required=True),
                'url': fields.char('rest URL', size=128, required=True),
                'param': fields.char('param', size=128, required=True),
                'jasper_url': fields.char('jasper URL', size=128, required=True),
                'format': fields.char('format', size=5, required=True),
                'organisation_type_id': fields.many2one('res.organisation.type', 'Organisatietype', select=True, ondelete='cascade'),
        }

web_report()

class res_function_type(osv.osv):
        _name = 'res.function.type'
        _inherit = 'res.function.type'

        _columns = {                
                'web_report_ids': fields.many2many('web.report', 'web_reports_function_type_rel', 'function_type_id', 'web_report_id', 'Rapporten'),
        }

res_function_type()

class res_organisation_function(osv.osv):
        _inherit = 'res.organisation.function'

        def _param_substitute_partner_id(self,param,partner_id):
            """
            substitute generic web_report param to a param linked to res_organisation_function
            """
            t = Template(param)
            return t.substitute(partner_id=partner_id)
        
        def _create_web_report_links(self,cr,uid,res_organisation_function_id,vals,context=None):
            if ( 'function_type_id' in vals and vals['function_type_id'] and
                 'partner_id' in vals and vals['partner_id'] ):
                web_report_download_obj = self.pool.get('web.report.download')
                res_partner_obj = self.pool.get('res.partner').browse(cr,uid,vals['partner_id'])                
                sql_stat = 'select web_report_id from web_reports_function_type_rel where function_type_id = %d' % (vals['function_type_id'], )
                cr.execute(sql_stat)
                for sql_res in cr.dictfetchall():                                        
                    web_report = self.pool.get('web.report').browse(cr,uid,sql_res['web_report_id'])
                    if res_partner_obj.organisation_type_id == web_report.organisation_type_id:                                                
                        param = self._param_substitute_partner_id(web_report.param,vals['partner_id'])
                        description = res_partner_obj.name
                        name = _(u'{0} {1}'.format(web_report.name,description))
                        web_report_download_id = web_report_download_obj.create(cr,uid, {
                            'name':name,
                            'web_report_id':web_report.id,
                            'res_organisation_function_id':res_organisation_function_id,
                            'format':web_report.format,
                            'param':param }, context=context )                         

        def create(self,cr,uid,vals,context=None):            
            res = super(res_organisation_function, self).create(cr,uid,vals,context=context)            
            self._create_web_report_links(cr,uid,res,vals,context=context)
            return res 

        def write(self,cr,uid,ids,vals,context=None):            
            web_report_download_obj = self.pool.get('web.report.download')
            
            #delete web report download links when we update a organisation function
            web_report_ids = web_report_download_obj.search(cr,uid,[('res_organisation_function_id','=',ids[0])],context=context) 
            if web_report_ids:
                web_report_download_obj.unlink(cr,uid,web_report_ids,context=context)     
            
            res = super(res_organisation_function, self).write(cr,uid,ids,vals,context=context)
            
            #recreate the web report download links for a organisation function
            obj = self.browse(cr, uid, ids)[0]
            vals['function_type_id'] = obj.function_type_id.id if not('function_type_id' in vals) else vals['function_type_id']             
            vals['partner_id'] = obj.partner_id.id if not('partner_id' in vals) else vals['partner_id']
            self._create_web_report_links(cr,uid,ids[0],vals,context=context)
            return res            
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: