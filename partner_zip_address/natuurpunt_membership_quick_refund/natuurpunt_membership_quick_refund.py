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
from tools.translate import _
import time

class membership_quick_refund_wizard(osv.osv_memory):

    _name = 'membership.quick.refund.wizard'
    
    _columns = {
        'reason': fields.char("Reden", size=64, required=True),
    }

    def quick_refund(self, cr, uid, ids, context=None):
        """Make a quick refund of the invoice"""
        print "CONTEXT:",context

        wiz = self.browse(cr, uid, ids[0])
        refund_wiz = self.pool.get('account.invoice.refund')
        mline_obj = self.pool.get('membership.membership_line')
        mline = mline_obj.browse(cr, uid, context['active_id'])

        vals={}
        vals['filter_refund'] = 'cancel'
        vals['description'] = wiz.reason
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('code','=','LIDC')])
        if not journal_ids or len(journal_ids) > 1:
            raise osv.except_osv(_('Error!'), _('No refund journal could be found.'))
        vals['journal_id'] = journal_ids[0]
        vals['date'] = time.strftime('%Y-%m-%d')
        vals['period'] = self.pool.get('account.period').find(cr, uid, dt=vals['date'], context=context)[0]

        print "REFUND WIZ VALS:",vals
        refund_wiz_id = self.pool.get('account.invoice.refund').create(cr, uid, vals, context=context)
        print "REFUND WIZ ID:",refund_wiz_id

        context['skip_write'] = True
        context['active_ids'] = [mline.account_invoice_id.id]
        refund_res = self.pool.get('account.invoice.refund').compute_refund(cr, uid, [refund_wiz_id], mode='cancel', context=context)
        print "REFUND RES:",refund_res

        return refund_res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
