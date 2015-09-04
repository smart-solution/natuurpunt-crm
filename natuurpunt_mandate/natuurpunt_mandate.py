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
from datetime import datetime
from datetime import time
from datetime import date
from dateutil.relativedelta import relativedelta
import re

class res_partner(osv.osv):
    _inherit = "res.partner"
    
    def create_form_bank_mandate_invoice(self, cr, uid, ids, context=None):
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','partner.create.bank.mandate.invoice'),
                                                            ('name','=','view.partner.create.bank.mandate.invoice.form')])

        partner = self.browse(cr, uid, ids)[0]
        if partner.id:
            context['default_partner_id'] = partner.id
            context['default_signature_date'] = datetime.today().strftime('%Y-%m-%d')
    
            return {
                'type': 'ir.actions.act_window',
                'name': 'Bank/Mandaat/Factuur Aanmaken',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view_id[0],
                'res_model': 'partner.create.bank.mandate.invoice',
                'target': 'new',
                'context': context,
                }
    
    _columns = {
        }
        
res_partner()

class partner_create_bank_mandate_invoice(osv.osv_memory):
    _name = "partner.create.bank.mandate.invoice"

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'bic_id': fields.many2one('res.bank', 'BIC Code', select=True),
        'bank_account': fields.char('Bankrekening', size=20),
        'unique_mandate_reference': fields.char('Unique Mandate Reference', size=35),
        'signature_date': fields.date('Date of Signature of the Mandate'),
        'membership_product_id': fields.many2one('product.product', 'Product Lidmaatschap', select=True),
        'membership_origin_id': fields.many2one('res.partner.membership.origin', 'Herkomst Lidmaatschap', select=True),
		'recruiting_organisation_id': fields.many2one('res.partner', 'Wervende Organisatie', select=True),
        'scan': fields.binary('Scan van het Mandaat'),
        'next_year_mandate': fields.boolean('Mandaat volgend jaar'),
        'mandate_only': fields.boolean('Enkel mandaat aanmaken'),
    }

    _defaults = {
         'mandate_only': False,
#        'unique_mandate_reference': lambda self, cr, uid, ctx: self.pool['ir.sequence'].get(cr, uid, 'sdd.mandate.reference'),
    }

    def onchange_future_date(self, cr, uid, ids, input_date, context=None):
        res = {}
        warning = ''
        if input_date > datetime.today().strftime('%Y-%m-%d'):
                warning = 'Datum mag niet in de toekomst liggen'
        if not (warning == ''):
            raise osv.except_osv(_('Fout: '), _(warning))
            return False
        else:
            return True

    def onchange_bankacct(self, cr, uid, ids, partner_id, bank_account, context=None):
        res = {}
        warning = ''
        warning_msg = {}

        if partner_id and bank_account:
            sql_stat = "select res_partner.id, res_partner.name, res_partner.ref from res_partner_bank, res_partner where replace(acc_number, ' ', '') = replace('%s', ' ', '') and res_partner_bank.partner_id <> %d and res_partner.id = res_partner_bank.partner_id" % (bank_account, partner_id, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if warning == '':
                    warning = '''De volgende contacten zijn reeds geregistreerd met dit rekeningnummer: 
''' + sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                else:
                    warning = warning + ', ' + sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                warning = warning + ''' 
'''
            sql_stat = "select sdd_mandate.id from sdd_mandate, res_partner_bank where sdd_mandate.partner_bank_id = res_partner_bank.id and res_partner_bank.partner_id = %d and sdd_mandate.state in ('valid','draft')" % (partner_id, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if warning == '':
                    warning = 'Let op: Partner heeft reeds andere mandaten.'
                else:
                    warning = warning + 'Let op: Partner heeft reeds andere mandaten.'
                warning = warning + ''' 
'''

            sql_stat = '''select date_from, date_to, membership_membership_line.state, extract(year from date_from) as year_from, extract(year from date_to) as year_to
from membership_membership_line
inner join product_product on (product_product.id = membership_membership_line.membership_id and product_product.membership_product = True)
where membership_membership_line.partner = %d and not(membership_membership_line.state = 'canceled')
''' % (partner_id, )
            cr.execute(sql_stat)
            today = date.today()
            year_today = today.year
            for sql_res in cr.dictfetchall():
                year_from_membership = int(sql_res['year_from'])
                year_to_membership = int(sql_res['year_to'])
                if sql_res['state'] == 'invoiced' and year_from_membership <= year_today:
                    if warning == '':
                        warning = 'Let op: Partner heeft reeds een ander gefactureerd lidmaatschap van jaar ' + str(year_from_membership) + ' tot ' + str(year_to_membership)
                    else:
                        warning = warning + 'Let op: Partner heeft reeds een ander gefactureerd lidmaatschap van jaar ' + str(year_from_membership) + ' tot ' + str(year_to_membership)
                    warning = warning + ''' 
    '''
                if sql_res['state'] == 'paid' and not(year_to_membership < year_today):
                    if warning == '':
                        warning = 'Let op: Partner heeft reeds een ander betaald lidmaatschap van jaar ' + str(year_from_membership) + ' tot ' + str(year_to_membership)
                    else:
                        warning = warning + 'Let op: Partner heeft reeds een andere betaald lidmaatschap van jaar ' + str(year_from_membership) + ' tot ' + str(year_to_membership)
                    warning = warning + ''' 
    '''
                    
        if not (warning == ''):
            warning_msg = { 
                    'title': _('Warning!'),
                    'message': _('''
%s''' % (warning))
                }   
            return {'warning': warning_msg}
        return res

    def create_bank_mandate_invoice(self, cr, uid, ids, context=None):
        res = {}
        partner_obj = self.pool.get('res.partner')
        for partner in self.browse(cr, uid, ids, context):
            sql_stat = "select id from res_partner_bank where partner_id = %d and replace(acc_number,' ','') = replace('%s',' ','')" % (partner.partner_id.id, partner.bank_account)
            cr.execute(sql_stat)
            sql_res = cr.dictfetchone()
            if sql_res:
                partner_bank_id = sql_res['id']
            else:
                partner_bank_obj = self.pool.get('res.partner.bank')
                partner_bank_id = partner_bank_obj.create(cr, uid, {
                    'bank_name': partner.bic_id.bic,
                    'owner_name': partner.partner_id.name,
                    'sequence': 50,
                    'street': partner.partner_id.street,
                    'partner_id': partner.partner_id.id,
                    'bank': partner.bic_id.id,
                    'bank_bic': partner.bic_id.bic,
                    'city': partner.partner_id.city,
                    'name': partner.partner_id.name,
                    'zip': partner.partner_id.zip,
                    'country_id': 21,
                    'state': 'iban',
                    'acc_number': partner.bank_account,
                    }, context=context)  

            mandate_obj = self.pool.get('sdd.mandate')
            mandate_id = mandate_obj.create(cr, uid,{
                'partner_bank_id': partner_bank_id,
                'partner_id': partner.partner_id.id,
    #            'company_id': ,
    #            'unique_mandate_reference': partner.unique_mandate_reference,
                'type': 'recurrent',
                'recurrent_sequence_type': 'first',
                'signature_date': partner.signature_date,
                'scan': False,
                'last_debit_date': None,
                'state': 'valid',
                'sepa_migrated': True,
                'original_mandate_identification': None,
                'scan': partner.scan,
                }, context=context)

            context['mandate_id'] = mandate_id
   
#            if partner.scan:
#                company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
#                attach_id = self.pool.get('ir.attachment').create(cr, uid, {
#                    'name': 'mandate.pdf',
#                    'datas_fname': 'mandate.pdf',
#                    'datas': partner.scan,
#                    'res_model': 'sdd.mandate',
#                    'res_id': mandate_id,
#                    'res_name': partner.unique_mandate_reference,
#                    'company_id': company_id,
#                }, context=context)
     
            cr.commit()
     
            if not partner.mandate_only:
                if not partner.next_year_mandate:
                    invoice_obj = self.pool.get('account.invoice')
                    invoice_line_obj = self.pool.get('account.invoice.line')
                    invoice_tax_obj = self.pool.get('account.invoice.tax')
             
                    product_id = partner.membership_product_id.id
                    analytic_dimension_1_id = partner.membership_product_id.analytic_dimension_1_id.id
                    analytic_dimension_2_id = partner.membership_product_id.analytic_dimension_2_id.id
                    analytic_dimension_3_id = partner.membership_product_id.analytic_dimension_3_id.id
             
            #            amount_inv = partner.membership_product_id.product_tmpl_id.list_price
                    amount_inv = partner.membership_product_id.list_price
             
                    account_id = partner.partner_id.property_account_receivable and partner.partner_id.property_account_receivable.id or False
                    fpos_id = partner.partner_id.property_account_position and partner.partner_id.property_account_position.id or False
             
                    quantity = 1
                    
                    payment_term_obj = self.pool.get('account.payment.term')
                    payment_term = payment_term_obj.search(cr, uid, [('name','=','Direct debit')])
                    payment_term_rec = payment_term_obj.browse(cr, uid, payment_term[0])
                    payment_term_id = payment_term_rec.id
                         
                    line_value = {}
                    line_dict = invoice_line_obj.product_id_change(cr, uid, {}, product_id, False, quantity, '', 'out_invoice', partner.partner_id.id, fpos_id, price_unit=amount_inv, context=context)
                    line_value.update(line_dict['value'])
                    line_value['price_unit'] = amount_inv
                    if line_value.get('invoice_line_tax_id', False):
                        tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                        line_value['invoice_line_tax_id'] = tax_tab
                    line_value['analytic_dimension_1_id'] = analytic_dimension_1_id
                    line_value['analytic_dimension_2_id'] = analytic_dimension_2_id
                    line_value['analytic_dimension_3_id'] = analytic_dimension_3_id
                    line_value['product_id'] = product_id
             
                    today = datetime.today()
    #                days30 = datetime.timedelta(days=30)
                    datedue = today + relativedelta( days = +30 )
             
                    reference = invoice_obj.generate_bbacomm(cr, uid, ids, 'out_invoice', 'bba', partner.partner_id.id, '', context={})
                    referenc2 = reference['value']['reference']
             
                    invoice_id = invoice_obj.create(cr, uid, {
                        'partner_id': partner.partner_id.id,
                        'membership_partner_id': partner.partner_id.id,
                        'account_id': account_id,
                        'membership_invoice': True,
                        'third_payer_id': None,
                        'third_payer_amount': 0.00,
                        'fiscal_position': fpos_id or False,
                        'payment_term': payment_term_id,
                        'sdd_mandate_id': mandate_id,
                        'partner_bank_id': partner_bank_id,
                        'reference_type': 'bba',
                        'type': 'out_invoice',
                        'reference': referenc2,
                        'date_due': datedue,
                        'internal_number': None,
                        'number': None,
                        'move_name': None,
                    }, context=context)
             
                    line_value['invoice_id'] = invoice_id
                    context['web_invoice_id'] = invoice_id
                    invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
                    invoice_obj.write(cr, uid, invoice_id, {'invoice_line': [(6, 0, [invoice_line_id])]}, context=context)
                    if 'invoice_line_tax_id' in line_value and line_value['invoice_line_tax_id']:
                        tax_value = invoice_tax_obj.compute(cr, uid, invoice_id).values()
                        for tax in tax_value:
                            invoice_tax_obj.create(cr, uid, tax, context=context)
             
                    wf_service = netsvc.LocalService('workflow')
                    wf_service.trg_validate(uid, 'account.invoice', invoice_id, 'invoice_open', cr) 

            if partner.membership_origin_id:
                sql_stat = '''update res_partner set membership_origin_id = %d where id = %d''' % (partner.membership_origin_id.id, partner.partner_id.id, )
                cr.execute(sql_stat)

            if partner.recruiting_organisation_id:
                sql_stat = '''update res_partner set recruiting_organisation_id = %d where id = %d''' % (partner.recruiting_organisation_id.id, partner.partner_id.id, )
                cr.execute(sql_stat)
     
            cr.commit()
         
        if not('web' in context):
            view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','document.cmis.link'),
                                                                ('name','=','document.cmis.link.form')])

            return {
                'type': 'ir.actions.act_window',
                'name': 'Scan van het Mandaat',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view_id[0],
                'res_model': 'document.cmis.link',
                'target': 'new',
                'context': context,
            }
        else:
            return {'type':'ir.actions.act_window_close','context': context,}

partner_create_bank_mandate_invoice()

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
                    if invoice.sdd_mandate_id:
        	            vals['sdd_mandate_id'] = invoice.sdd_mandate_id.id
        return super(payment_line, self).create(cr, uid, vals, context=context)

payment_line()

class res_partner_bank(osv.osv):
    _inherit = 'res.partner.bank'

    def _function_mandate_state(self, cr, uid, ids, name, arg, context=None):
        res = {}
        mandate_state = ''
        print 'IDS:',ids
        for line in self.browse(cr, uid, ids):
            nbr_draft = 0
            nbr_valid = 0
            nbr_cancel = 0
            nbr_invalid = 0
            res[line.id] = None
            if line.sdd_mandate_ids:
                for mandate in line.sdd_mandate_ids:
                    if mandate.state == 'draft':
                        nbr_draft += 1
                    else:
                        if mandate.state == 'valid':
                            nbr_valid += 1
                        else:
                            if mandate.state == 'cancel':
                                nbr_cancel += 1
                            else:
                                nbr_invalid += 1
                if nbr_valid != 0:
                    mandate_state = 'Geldig'
                    res[line.id] = mandate_state
                elif nbr_draft != 0:
                    mandate_state = 'Concept'
                    res[line.id] = mandate_state
                elif nbr_cancel != 0:
                    mandate_state = 'Geannuleerd'
                    res[line.id] = mandate_state
                elif nbr_invalid != 0:
                    mandate_state = 'Ongeldig'
                    res[line.id] = mandate_state
        return res

    def onchange_bankacct(self, cr, uid, ids, bank_account, context=None):
        res = {}
        warning = ''

        if bank_account:
            sql_stat = "select res_partner.id, res_partner.name, res_partner.ref from res_partner_bank, res_partner where replace(acc_number, ' ', '') = replace('%s', ' ', '') and res_partner.id = res_partner_bank.partner_id" % (bank_account, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if warning == '':
                    warning = sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                else:
                    warning = warning + ', ' + sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                warning = warning + ''' 
'''

        if not (warning == ''):
            warning_msg = { 
                    'title': _('Warning!'),
                    'message': _('''De volgende contacten zijn reeds geregistreerd met dit rekeningnummer: 
%s''' % (warning))
                }   
            return {'warning': warning_msg}
        return res

    _columns = {
        'mandate_state': fields.function(_function_mandate_state, string='Status Mandaat', type='char'),
    }

res_partner_bank()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
