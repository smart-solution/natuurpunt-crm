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


class ir_attachment(osv.osv):

    _inherit = 'ir.attachment'

    def _data_get(self, cr, uid, ids, name, arg, context=None):
        return super(ir_attachment, self)._data_get(cr, uid, ids, name, arg, context=context)

    def _data_set(self, cr, uid, id, name, value, arg, context=None):
        # We dont handle setting data to null
        if not value:
            return True
        if context is None:
            context = {}
        server_mode = self.pool.get('ir.config_parameter').get_param(cr, uid, 'document_cmis.server_mode')
        if server_mode == 'cmis_only':
            return True
        return super(ir_attachment, self)._data_set(cr, uid, id, name, value, arg, context=context)


    _columns = {
        'cmis_object_id': fields.char('CMIS Directory ID', size=256),
        'datas': fields.function(_data_get, fnct_inv=_data_set, string='File Content', type="binary", nodrop=True),
    }


    def create(self, cr, uid, vals, context=None):
        """Send the document to the CMIS server and create the attachment"""

        if 'res_model' in vals and vals['res_model']:
            #Find ressource directories
            model_id = self.pool.get('ir.model').search(cr, uid, [('model','=',vals['res_model'])])[0]
            dirs = self.pool.get('document.directory').search(cr, uid, [('ressource_type_id','=',model_id)])
            ressource = self.pool.get(vals['res_model']).browse(cr, uid, vals['res_id'])
            server_mode = self.pool.get('ir.config_parameter').get_param(cr, uid, 'document_cmis.server_mode')
            if not dirs and server_mode == 'cmis_only':
                raise osv.except_osv(_("Error!"),_("You cannot add attachments to this record"))

            dir_found = False

            for directory in self.pool.get('document.directory').browse(cr, uid, dirs):
                # Process only for CMIS enabled directories
                if directory.cmis_object_id:    

                    # Check the directory domain
                    domain = [('id','=',vals['res_id'])] + eval(directory.domain)
                    res_ids = self.pool.get(vals['res_model']).search(cr, uid, domain)
                    if not res_ids:
                        continue

                    dir_found = True    
            
                    # Check if the directory is company specific
                    if ressource.company_id != directory.company_id and directory.company_id:
                        raise osv.except_osv(_("Error!"),_("You cannot attach a document from the company %s in a directory from the company %s"%(ressource.company_id.name,directory.company_id.name)))

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

                        # Check which field to use to find the name
                        if directory.resource_field:
                            name_field = directory.resource_field.name
                            name = str(getattr(ressource, name_field))
                        else:
                            name = str(ressource.name)

                        if vals['res_model'] == 'account.invoice':
                            name = ressource.internal_number or ressource.number or str(ressource.id)

                        query = """ 
                            select cmis:objectId, cmis:name
                            from cmis:folder
                            where in_folder('%s') and cmis:name = '%s'
                            order by cmis:lastModificationDate desc
                            """ % (cmisDir,name)
                        childrenRS = repo.query(query)
                        children = childrenRS.getResults()

                        res_found = False

                        # If no name is found
                        if not name:
                            raise osv.except_osv(_('Error!'),_("Cannot find a document name for this ressource (model:%s / id:%s)"%(vals['res_model'],vals['res_id'])))

                        name = str(name).replace('/','_')

                        # Check if the folder already exists
                        for child in children:
                            if name == child.properties['cmis:name']:
                                # Use the ressource folder
                                cmisDir = repo.getObject(child.properties['cmis:objectId'])
                                res_found = True
                        if not res_found:
                            # Create the ressouce folder
                            try:
                                cmisDir = repo.createFolder(cmisDir, name)
                            except:
                                raise osv.except_osv(_('Error!'),_("You cannot add that document in the CMIS Server."))
                            

                    # Create the temporary file
                    # NiceToHave: Create temp file for big files (>1Go) and in memory for smaller ones
                    fname = vals['datas_fname']
                    extension =  fname.split(".")
                    # Keep the last extension (for .tar.gz it will be .gz)
                    if len(extension) == 1:
                        # If not extension found, set as txt
                        extension = ".txt"
                    else:
                        extension = "." + extension[-1]

                    # Check if a file already exists with the same name for the same ressouce
                    # NiceToHave: Use versioning when updating the same documents
                    oldres = self.search(cr, uid, [('name','=',name),('res_id','=',vals['res_id'])])
                    if self.search(cr, uid, [('name','=',fname),('res_id','=',vals['res_id'])]):
                        raise osv.except_osv(_("Error!"),_("A document already exists with the same name for this ressource (model:%s / id:%s)"%(vals['res_model'],vals['res_id'])))

                    fp = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
                    fp.write(base64.decodestring(vals['datas']))
                    fp.close()
                    fdata = open(fp.name,'r')

                    #fdata = io.BytesIO(base64.decodestring(vals['datas']))    
                    #fdata = io.StringIO(unicode(vals['datas']))        
                    try:
                        newDoc = cmisDir.createDocument(vals['datas_fname'], contentFile=fdata)
                    except:
                        raise osv.except_osv(_('Error!'),_("Cannot create that document in the CMIS Server."))

                    fdata.close()

                    # Get the cmis object id and store it in the attachment
                    link_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'document_cmis.server_link_url')
                    url = link_url + newDoc.properties['cmis:objectId']
                
                    vals['type'] = 'url'
                    vals['url'] = url
                    vals['cmis_object_id'] = newDoc.properties['cmis:objectId']
                    vals['db_datas'] = ""
        
            if server_mode == 'cmis_only' and not dir_found:
                # Does not attach document if no CMIS ID is specified and server mode is cmis_only
                # Or else fallback to OpenERP DMS
                raise osv.except_osv(_("Error!"),_("You cannot add attachments to this record"))

            gc.collect()

        return super(ir_attachment, self).create(cr, uid, vals, context)


    def unlink(self, cr, uid, ids, context=None):
        """Delete the cmis document when a ressource is deleted"""
        for doc in self.pool.get('ir.attachment').browse(cr, uid, ids):
            if doc.type == 'url':
                repo = cmis_connect(cr, uid)
                if not repo:
                    raise osv.except_osv(_('Error!'),_("Cannot find the root directory for OpenERP in the CMIS Server."))

                for attachment in self.browse(cr, uid, ids):
                    if attachment.cmis_object_id:
                        try:
                            doc = repo.getObject(attachment.cmis_object_id)
                            doc.delete()
                        except:
                            raise osv.except_osv(_("Error!"),_("Cannot delete that document in the CMIS Server: %s"%(attachment.name)))

        return super(ir_attachment, self).unlink(cr, uid, ids, context=context)


class document_directory(osv.osv):

    _inherit = 'document.directory'

    _columns = {
        'cmis_object_id': fields.char('CMIS Object ID', size=256),
    }

    def cmis_sync(self, cr, uid, ids, context=None):
        """Try to create directories in the DMS"""
        for directory in self.browse(cr, uid, ids):

            if not directory.cmis_object_id and directory.type == "ressource":

                if not directory.company_id:
                    raise osv.except_osv(_('Error!'),_("You must assign a company to this directory (%s) to use the Sync with DMS feature."%(dir.name)))

                company = self.pool.get('res.company').browse(cr, uid, directory.company_id.id)
                if not company.cmis_base_dir:
                    raise osv.except_osv(_('Error!'),_("You must assign a CMIS base directory to this company (%s) to use the Sync with DMS feature."%(company.name)))

                repo = cmis_connect(cr, uid)
                if not repo:
                    raise osv.except_osv(_('Error!'),_("Cannot find the default repository in the CMIS Server."))

                # Find the company base CMIS directory
                try:
                    cmisDir = repo.getObject(company.cmis_base_dir)
                except:
                    raise osv.except_osv(_('Error!'),_("Cannot find that company base directory (%s) in the DMS. You may not have the right to access it."%(company.cmis_base_dir)))

                childrenRS = cmisDir.getChildren()
                children = childrenRS.getResults()
                res_found = False

                # Check if the folder already exists
                for child in children:
                    if directory.name == child.properties['cmis:name']:
                        # Use the ressource folder
                        cmisDir = repo.getObject(child.properties['cmis:objectId'])
                        self.write(cr, uid, [directory.id], {'cmis_object_id':cmisDir})
                        res_found = True
                if not res_found:
                    # Create the ressouce folder
                    cmisDir = repo.createFolder(cmisDir, directory.name)
                    dirID = repo.getObject(cmisDir.properties['cmis:objectId'])
                    self.write(cr, uid, [directory.id], {'cmis_object_id':dirID})

        return True


class res_company(osv.osv):

    _inherit = 'res.company'

    _columns = {
        'cmis_base_dir': fields.char('CMIS Base Directory', size=256),
    }

class document_directory_cmis_sync(osv.osv_memory):

    _name= "document.directory.cmis.sync"

    def cmis_sync(self, cr, uid, ids, context=None):
        return self.pool.get('document.directory').cmis_sync(cr, uid, context['active_ids'], context=context)




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
