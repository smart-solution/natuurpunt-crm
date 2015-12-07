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
import time
import re
from datetime import datetime

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
                    invoice = invoice_obj.browse(cr, uid, invoice_id[0])
                    if invoice.journal_id.code == 'LID':
        	            vals['communication'] = 'Lidmaatschap'
                    if invoice.journal_id.code == 'GIFT':
                        vals['communication'] = 'Gift %s' % (invoice.donation_id.analytic_account_id.name, )
                    if invoice.sdd_mandate_id:
                        vals['bank_id'] = invoice.sdd_mandate_id.partner_bank_id.id
                        vals['sdd_mandate_id'] = invoice.sdd_mandate_id.id

        return super(payment_line, self).create(cr, uid, vals, context=context)

payment_line()

class wizard_partner_to_renew(osv.osv_memory):
    _name = 'wizard.partner.to.renew'

    _columns = {
        'end_date_membership': fields.date('Einddatum Lidmaatschap'),
    }

    defaults = {
        'end_date_membership': time.strftime('%Y-%m-%d'),
    }

    def find_members_to_renew(self, cr, uid, ids, context=None):
        partner_obj = self.pool.get('res.partner')
        mod_obj = self.pool.get('ir.model.data')
        membership_obj = self.pool.get('membership.membership_line')

        wiz = self.browse(cr, uid, ids)[0]

        end_date_membership = wiz.end_date_membership
        if not end_date_membership:
            end_date_membership = datetime.today().strftime('%Y-12-31')
        
        args = [('deceased','=',False),
                ('free_member','=',False),
                ('third_payer_id','=',False),
                ('active','=',True)]

        partner_ids = partner_obj.search(cr, uid, args=args, context=context)
        print "PARTNER IDS:",len(partner_ids)

        member_ids = []

        # Find all active membership lines
        for partner_id in partner_ids:
            membership_lines = self.pool.get('res.partner').active_membership_line_find(cr, uid, partner_id, end_date_membership, context=context)
            print "################################### PARTNER:",partner_id
            print "############## MEMBERSHIP LINES:",membership_lines
            if membership_lines:
                # Check if a membership already exist after the date
                domain = [('partner','=', partner_id),('date_to','>', end_date_membership),('|',('state','=','paid'),('membership_renewal','=',True))]
                exist_line_ids = self.pool.get('membership.membership_line').search(cr, uid, domain)
                if exist_line_ids:
                    print "######### Already paid member"
                    continue

                member_ids.append(partner_id)    

        try:
            tree_view_id = mod_obj.get_object_reference(cr, uid, 'membership', 'membership_members_tree')[1]
        except ValueError:
            tree_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'base', 'view_partner_form')[1]
        except ValueError:
            form_view_id = False

        return {'name': _('Niet-hernieuwde leden vinden'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'res.partner',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'type': 'ir.actions.act_window',
                'domain': [('id','in',member_ids)]
        }

class membership_renew(osv.osv_memory):
    """Membership renew"""

    _name = "membership.renew"
    _description = "Membership Renew Wizard"

    def membership_renew(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')
        datas = {}
        if context is None:
            context = {}

        renew_list = []

        for partner in self.pool.get('res.partner').browse(cr, uid, context.get('active_ids', [])):

            # If no renewal product is specified use Gewoon Lid
            datas = { 
                'membership_product_id': partner.membership_renewal_product_id.id or 2,
                'membership_renewal':True,
                'amount': partner.membership_renewal_product_id.list_price or 27.0,
            }
            renew_list.append(partner_obj.create_membership_invoice(cr, uid, [partner.id], datas=datas, context=context))
            cr.commit()

        try:
            search_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')[1]
        except ValueError:
            search_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')[1]
        except ValueError:
            form_view_id = False

        return  {
            'domain': [('id', 'in', renew_list)],
            'name': 'Renew Membership',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_id, 'form')],
            'search_view_id': search_view_id,
        }

        return True

membership_renew()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
