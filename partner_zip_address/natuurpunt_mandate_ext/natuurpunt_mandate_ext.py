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
from openerp import netsvc
import re

class payment_line(osv.osv):
    _inherit = 'payment.line'

    def create(self, cr, uid, vals, context=None):
        if 'move_line_id' in vals and vals['move_line_id']:
            move_obj = self.pool.get('account.move.line')
            move_id = move_obj.search(cr, uid, [('id', '=', vals['move_line_id'])])
            if move_id and len(move_id) > 0:
                move_line_id = move_obj.browse(cr, uid, move_id[0])
                invoice_obj = self.pool.get('account.invoice')
                invoice_id = invoice_obj.search(cr, uid, [('move_id', '=', move_line_id.move_id.id)])
                if invoice_id and len(invoice_id) > 0:
                    print 'invoice found'
                    invoice = invoice_obj.browse(cr, uid, invoice_id[0])
                    print 'journal:', invoice.journal_id.code
                    print 'mandaat:', invoice.sdd_mandate_id
                    if invoice.journal_id.code == 'LID':
        	            vals['communication'] = 'Lidmaatschap'
                    if invoice.journal_id.code == 'GIFT':
                        vals['communication'] = 'Gift %s' % (invoice.donation_id.analytic_account_id.name, )
                    if invoice.sdd_mandate_id:
                        vals['bank_id'] = invoice.sdd_mandate_id.partner_bank_id.id
                        vals['sdd_mandate_id'] = invoice.sdd_mandate_id.id

        return super(payment_line, self).create(cr, uid, vals, context=context)

payment_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
