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


class wizard_giften_to_create(osv.osv_memory):
    _name = 'wizard.giften.to.create'

    _columns = {
        'end_date_donation': fields.date('Laatste factuurdatum'),
    }

    defaults = {
        'end_date_donation': time.strftime('%Y-%m-%d'),
    }

    def find_giften_to_create(self, cr, uid, ids, context=None):
        partner_obj = self.pool.get('res.partner')
        mod_obj = self.pool.get('ir.model.data')
        donation_obj = self.pool.get('donation.partner.account')

        wiz = self.browse(cr, uid, ids)[0]

        last_inv_date = wiz.end_date_donation
        if not last_inv_date:
            last_inv_date = datetime.today().strftime('%Y-12-31')
        context['last_inv_date'] = last_inv_date
        
        args = [('deceased','=',False),
                ('free_member','=',False),
                ('third_payer_id','=',False),
                ('active','=',True)]

        partner_ids = partner_obj.search(cr, uid, args=args, context=context)

        donation_ids = self.pool.get('donation.partner.account').search(cr, uid, [
            '|',
            ('next_invoice_date', '=', False),
            ('next_invoice_date', '<=', last_inv_date),
            ('donation_start', '<=', last_inv_date),
            ('donation_cancel', '=', False),
            ('partner_id', 'in', partner_ids),
        ], context=context)

        member_ids = []
        dona_ids = []

        # Find donation to invoice
        for donation in self.pool.get('donation.partner.account').browse(cr, uid, donation_ids):
            # Check for a valid mandate 
            mandate_ids = self.pool.get('sdd.mandate').search(cr, uid, [('state','=','valid'),('partner_id','=',donation.partner_id.id)])
            if mandate_ids:
                member_ids.append(donation.partner_id.id)
                dona_ids.append(donation.id)
#        print "DONATION IDS:",member_ids

        context['donation_ids'] = dona_ids
#        print "CONTEXT 1:",context

        try:
            tree_view_id = mod_obj.get_object_reference(cr, uid, 'membership', 'membership_members_tree')[1]
        except ValueError:
            tree_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'base', 'view_partner_form')[1]
        except ValueError:
            form_view_id = False

        return {'name': _('Giften facturen maken'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'res.partner',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'type': 'ir.actions.act_window',
                'domain': [('id','in',member_ids)]
        }

class wizard_giften_invoice_create(osv.osv_memory):
    """Membership renew"""

    _name = "wizard.giften.invoice.create"
    _description = "Giften Create Wizard"

    _columns = {
        'end_date_donation': fields.date('Laatste factuurdatum'),
    }

    defaults = {
#        'end_date_donation': context['last_inv_date']
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        print "CONTEXT DGET:",context
        result = super(wizard_giften_invoice_create, self).default_get(cr, uid, fields, context=context)
        if 'last_inv_date' in context and context['last_inv_date']:
            result['last_inv_date'] = context['last_inv_date']
        return result


    def giften_invoice_create(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')

        datas = False
        product_id = False

        if context is None:
            context = {}
        print "CONTEXT 2:",context

        wiz = self.browse(cr, uid, ids)[0]
        last_inv_date = wiz.end_date_donation
        if not last_inv_date:
            last_inv_date = datetime.today().strftime('%Y-12-31')

        renew_list = []

        donation_ids = self.pool.get('donation.partner.account').search(cr, uid, [
            '|',
            ('next_invoice_date', '=', False),
            ('next_invoice_date', '<=', last_inv_date),
            ('donation_start', '<=', last_inv_date),
            ('donation_cancel', '=', False),
            ('partner_id', 'in', context['active_ids']),
        ], context=context)

        renew_list.append(self.pool.get('donation.partner.account').create_donation_invoice(cr, uid, donation_ids, product_id=product_id, datas=datas, context=context))

#        for donation in donation_ids:
#            inv_ids = self.pool.get('account.invoice').search(cr, uid, [('donation_id','=',donation)])
#            if inv_ids:
#                continue
#            renew_list.append(partner_obj.create_donation_invoice(cr, uid, [donation], datas=datas, context=context))

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
            'name': 'Giften factuuren',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_id, 'form')],
            'search_view_id': search_view_id,
            'context':context
        }

        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
