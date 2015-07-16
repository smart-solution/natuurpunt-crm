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
from cmislib.model import CmisClient, Repository
import base64
import logging
_logger = logging.getLogger(__name__)


class document_cmis_link(osv.osv_memory):

    _inherit = 'document.cmis.link'

    def default_get(self, cr, uid, fields, context=None):
        """Load the CMIS drop-off documents in memory"""
        if 'active_model' in context and (context['active_model'] == 'partner.create.bank.mandate.invoice' or context['active_model'] == 'res.partner') and ('mandate_id' in context and context['mandate_id']):
            context['active_model'] = 'sdd.mandate'
            context['active_id'] = context['mandate_id']
        return super(document_cmis_link, self).default_get(cr, uid, fields, context=context)


    def cmis_document_link(self, cr, uid, ids, context=None):
        """Display the list of the documents found on the ressource cmis dropoff directory and allow to select and link a document as attachment"""
        if 'mandate_id' in context and context['mandate_id']:
            context['active_model'] = 'sdd.mandate'
            context['active_id'] = context['mandate_id']
        return super(document_cmis_link, self).cmis_document_link(cr, uid, ids, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
