#-*- coding: utf-8 -*-
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
from tools.translate import _
from datetime import datetime
from cmislib.model import CmisClient, Repository
import io
import base64
import tempfile
import logging
_logger = logging.getLogger(__name__)
from openerp import pooler
import gc
import resource

def using(point=""):
    usage=resource.getrusage(resource.RUSAGE_SELF)
    return '''%s: usertime=%s systime=%s mem=%s mb'''%(point,usage[0],usage[1], (usage[2]*resource.getpagesize())/1000000.0 )
                
def cmis_connect(cr, uid):
    """Connect to the CMIS Server and returns the document repository"""
    user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid)
    server_url = pooler.get_pool(cr.dbname).get('ir.config_parameter').get_param(cr, uid, 'document_cmis.server_url')

    if not server_url:
        raise osv.except_osv(_('Error!'),_("Cannot connect to the CMIS Server: No CMIS Server URL system property found"))

    client = CmisClient(server_url, user.login, user.password)
    repo = client.getDefaultRepository()

    return repo

class account_invoice(osv.osv):

    _inherit = "account.invoice"

    def invoice_validate(self, cr, uid, ids, context=None):    

        invs = self.browse(cr, uid, ids)
        draft_to_skip = []
        for inv in invs:
            if inv.internal_number:
                draft_to_skip.append(inv.id)

        res =  super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        model_id = self.pool.get('ir.model').search(cr, uid, [('model','=','account.invoice')])[0]
        dirs = self.pool.get('document.directory').search(cr, uid, [('ressource_type_id','=',model_id)])

        for invoice in self.browse(cr, uid, ids):

            # skip invoiced that have been resetted to draft
            if invoice.id in draft_to_skip:
                continue

            for directory in self.pool.get('document.directory').browse(cr, uid, dirs):
                # Process only for CMIS enabled directories
                if directory.cmis_object_id:    

                    repo = cmis_connect(cr, uid)
                    if not repo:
                        raise osv.except_osv(_('Error!'),_("Cannot find the default repository in the CMIS Server."))

                    # Find the CMIS directory
                    try:
                        cmisDir = repo.getObject(directory.cmis_object_id)
                    except:
                        raise osv.except_osv(_('Error!'),_("Cannot find this directory (%s) in the DMS. You may not have the right to access it."%(directory.name)))

                    if not cmisDir:
                        raise osv.except_osv(_('Error!'),_("Cannot find the directory %s in the CMIS Server: %s"%(directory.name)))

                    # For Static directories, of a CMIS Object ID is specified, it put all files in that directory (IOW, it does not create subdirs)
                    # For Folders per ressources, search if the ressource directory exists or creates it
                    if directory.type == "ressource":
                        query = """ 
                            select cmis:objectId, cmis:name
                            from cmis:folder
                            where in_folder('%s')
                            order by cmis:lastModificationDate desc
                            """ % cmisDir
                        childrenRS = repo.query(query)
                        #childrenRS = cmisDir.getChildren()
                        children = childrenRS.getResults()

                    # Check if the folder already exists
                    for child in children:
                        if str(invoice.id) == child.properties['cmis:name']:
                            # Modify the directory name                   
                            props = {}
                            props['cmis:name'] = invoice.number
                            child.updateProperties(props)

        return res


    _columns = {
        'record_id': fields.related('id', type='char', size=64, string='ID'),
    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
