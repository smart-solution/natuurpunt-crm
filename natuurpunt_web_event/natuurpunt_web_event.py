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
import datetime
import time
from openerp import netsvc
from tools.translate import _

def account_configurator(cr,uid,method=False):
    account_config = {
       'account_id' : '580200' if method == 'OGONE' else '740150',
       'analytic_dimension_1_id' : False if method == 'OGONE' else 'I07-02',
    }        
    def line_value(obj,column):
        code = account_config[column] if column in account_config else False
        if code:
           ids = obj.search(cr, uid, [('code','=',code)])
           if not ids:
              raise osv.except_osv(_('Error!'), _('Event account configurator error'%(column)))
           return obj.browse(cr, uid, ids[0]).id
        else:
           return False
    return line_value

def check_validate_event_ogone_payment(invoice,jrn):
    """
    first check the state of the invoice
    to check if an event invoice can be paid via OGONE, check the move lines
    as the invoice state is only changed when we process the bank statement
    """
    if invoice.state == 'paid':
        return True
    else:
        for line in invoice.move_id.line_id:
            if line.account_id == jrn.default_credit_account_id:
                return True
    return False

class event_event(osv.osv):
    _inherit = 'event.event'
    
    def create_web_event(self,cr,uid,ids,vals,context=None):
        """
        for website : create event + confirm event
        """
        context = context or {}
        if ids == None:
            ids = []
        try:
            ids.append(self.create(cr,uid,vals,context))
            self.button_confirm(cr,uid,ids,context)
        except:        
            return {'id':0}
        else:
            return {'id':ids[0]}

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    
    _columns = {
        'event_invoice': fields.boolean('Activiteitsfactuur'),
    }
    
    def _sync_registration(self, cr, uid, ids, mode='confirm', context=None):
        """
        keep state of invoice in sync with state of registration
        supported modes are confirm and cancel
        """
        registration_obj = self.pool.get('event.registration')
        registration_ids = registration_obj.search(cr, uid, [('invoice_id', 'in', ids)])
        if mode == 'confirm':
            registration_obj.confirm_registration(cr, uid, registration_ids, context=context)
        elif mode == 'cancel':
            registration_obj.write(cr, uid, registration_ids, {'state': 'cancel'})            
        else:
            raise osv.except_osv(_('Error!'), _('Unsupported registation mode:'%(mode)))
        return True        

    def confirm_paid(self, cr, uid, ids, context=None):
        """
        overide of method confirm_paid of account.invoice
        """
        if context is None:
            context = {}
        res = super(account_invoice, self).confirm_paid(cr, uid, ids, context=context)
        invoice = self.read(cr, uid, ids, ['event_invoice','type'], context=context)
        if res and invoice[0].get('event_invoice',False):
            if invoice[0].get('type',False) == 'out_invoice':
                self._sync_registration(cr, uid, ids, mode='confirm', context=context)
            else:
                return res 
        return res

    def get_refund_mode(self, cr, uid, ids, context=None):
        registration_obj = self.pool.get('event.registration')
        registration_ids = registration_obj.search(cr, uid, [('invoice_id', 'in', ids)])
        for registration in registration_obj.browse(cr, uid, registration_ids, context=context):
            if registration.state == 'open':
                return 'refund'
            else:
                return False
        else:
            return False
    
    def cancel_event_payment(self, cr, uid, ids, context=None):
        refund_inv_id = 0        
        try:        
            for invoice in self.browse(cr, uid, ids, context=context):
                if invoice.state == 'open':
                    refund_mode = 'cancel'
                elif invoice.state == 'paid':
                    refund_mode = self.get_refund_mode(cr, uid, ids, context=context)
                else:
                    refund_mode = False

                if refund_mode:
                    vals={}
                    vals['filter_refund'] = 'cancel'
                    vals['description'] = _('refund invoice {0}').format(invoice.internal_number)
                    vals['date'] = time.strftime('%Y-%m-%d')
                    vals['period'] = self.pool.get('account.period').find(cr, uid, dt=vals['date'], context=context)[0]          
                
                    #TO DO config journal on refund?                            
                    #default journaal van invoice
                    journal_ids = self.pool.get('account.journal').search(cr, uid, [('code','=','VFC')])
                    if journal_ids and len(journal_ids) == 1:
                
                        vals['journal_id'] = journal_ids[0]            
                          
                        refund_wiz_id = self.pool.get('account.invoice.refund').create(cr, uid, vals, context=context)

                        context['skip_write'] = True
                        context['active_ids'] = [invoice.id]
                        
                        refund_result = self.pool.get('account.invoice.refund').compute_refund(cr, uid, [refund_wiz_id], mode=refund_mode, context=context)

                        self._sync_registration(cr, uid, ids, mode='cancel', context=context)
        except:
            return {'id':refund_inv_id}
        else:
            return {'id':invoice.partner_id.id,'invoice_id':invoice.id,'supplier_invoice_number':invoice.supplier_invoice_number}
            
    def cancel_event(self, cr, uid, ids, context=None):
        try:
            self._sync_registration(cr, uid, ids, mode='cancel', context=context)
        except:
            return {'id':0}
        else:            
            for invoice in self.browse(cr, uid, ids, context=context):
                return {'id':invoice.partner_id.id,'invoice_id':invoice.id,'supplier_invoice_number':invoice.supplier_invoice_number}                        

    def validate_event_payment(self, cr, uid, ids, context=None):
        mv_obj = self.pool.get('account.move')
        mv_line_obj = self.pool.get('account.move.line')
        acc_analytic_obj = self.pool.get('account.analytic.account')

        try:
            for invoice in self.browse(cr, uid, ids, context):
                
                jrn_obj = self.pool.get('account.journal')
                jrn_ids = jrn_obj.search(cr, uid, [('code','=','OGON'),])
                jrn = jrn_obj.browse(cr, uid, jrn_ids[0])
                
                if mv_obj.search(cr,uid,[('journal_id','=',jrn.id),('ref','=',invoice.number)]):
                   raise osv.except_osv(_('Error!'), _("OGONE journal entry already exists:"%(invoice.move_id.name)))
               
                if check_validate_event_ogone_payment(invoice, jrn):
                    raise osv.except_osv(_('Error!'), _("Event invoice can not be paid with OGONE."))

                self._sync_registration(cr, uid, ids, mode='confirm', context=context)

                mv_vals = {
                    'ref': invoice.number,
                    'journal_id': jrn.id,
                    'date': datetime.date.today(),
                    'company_id': invoice.company_id.id,
                }
                mv_id = mv_obj.create(cr, uid, mv_vals)
                mv = mv_obj.browse(cr, uid, mv_id)

                debit_mv_line_vals = {
                   'move_id': mv_id,
                   'name': invoice.number,
                   'ref': mv.name.replace('/',''),
                   'partner_id': invoice.partner_id.id,
                   'account_id': jrn.default_debit_account_id.id,
                   'debit': invoice.residual,
                }
                debit_mv_line_id = mv_line_obj.create(cr, uid, debit_mv_line_vals)
                
                credit_mv_line_vals = {
                   'move_id': mv_id,
                   'name': invoice.number,
                   'ref': mv.name.replace('/',''),
                   'partner_id': invoice.partner_id.id,
                   'account_id': jrn.default_credit_account_id.id,
                   'analytic_dimension_1_id': account_configurator(cr,uid)(acc_analytic_obj,'analytic_dimension_1_id'),
                   'credit': invoice.residual,
                   'quantity': 1,
                }
                credit_mv_line_id = mv_line_obj.create(cr, uid, credit_mv_line_vals)
                
                mv_obj.button_validate(cr, uid, [mv_id], context=context)
                rec_line_id = False
                for line in invoice.move_id.line_id:
                    if line.account_id == invoice.account_id:
                        rec_line_id = line.id
                if not rec_line_id:
                    raise osv.except_osv(_('Error!'), _('No recociliation account could be found for the journal entry:'%(invoice.move_id.name)))

                #reconcile_ids = [credit_mv_line_id, rec_line_id]
                # Reconcile the journal entry
                #return mv_line_obj.reconcile(cr, uid, reconcile_ids, 'auto', False, False, False, context=context)
        except:
            return {'move_id':0}
        else:
            return {'move_id':mv_id}

account_invoice()

class event_registration(osv.osv):
    _inherit = 'event.registration'

    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice Reference', select=True),
        'log_event_web': fields.binary('binary log of web parameters'),
    }
    
class product_product(osv.osv):
    _inherit = 'product.product'
 
    _columns = {
        'event_product': fields.boolean('Event product'),
    }
    
class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def create_event_invoice(self, cr, uid, ids, selected_product_id=None, datas=None, context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_tax_obj = self.pool.get('account.invoice.tax')
        event_obj = self.pool.get('event.event')
        acc_obj = self.pool.get('account.account')
        acc_analytic_obj = self.pool.get('account.analytic.account')

        try:
            #event -> company
            event_id = datas.get('event_id',False)
            if not event_id:
                raise osv.except_osv(_('Error!'), _("Need event to make the invoice."))

            line_value_config = account_configurator(cr,uid,datas['method'])
            product = self.pool.get('product.product').read(cr, uid, selected_product_id, [], context=context)
            product_id = product[0].get('id',False)
            quantity = 1
            amount = datas.get('amount', 0.0)
            method = datas['method']
            invoice_id_list = []
            if type(ids) in (int, long,):
                ids = [ids]

            def invoice_line(amount):
                line_value = {
                    "product_id" : product_id,
                    "invoice_id" : invoice_id,
                }
                line_dict = invoice_line_obj.product_id_change(cr, uid, {},
                                                               product_id,
                                                               False,
                                                               quantity,
                                                               '',
                                                               'out_invoice',
                                                               partner_id,
                                                               fpos_id,
                                                               price_unit=amount,
                                                               context=context)
                line_value.update(line_dict['value'])
                line_value['price_unit'] = amount
                line_value['quantity'] = quantity
                if line_value.get('invoice_line_tax_id', False):
                    tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                    line_value['invoice_line_tax_id'] = tax_tab
                line_value['account_id'] = line_value_config(acc_obj,'account_id')
                line_value['analytic_dimension_1_id'] = line_value_config(acc_analytic_obj,'analytic_dimension_1_id')
                return line_value

            def register_event():
                registration_obj = self.pool.get('event.registration')
                vals = {
                    'name': partner.name,
                    'partner_id': partner_id,
                    'email': partner.email,
                    'phone': partner.phone,                    
                    'event_id': event_id,
                    'invoice_id': invoice_id
                }
                registration_id = registration_obj.create(cr, uid, vals, context=context)
                message = _("The registration been created for partner [%s] %s.") % (partner_id,partner.name)
                registration_obj.message_post(cr, uid, [registration_id], body=message, context=context)
                return registration_id

            for partner in self.browse(cr, uid, ids, context=context):
                
                fpos_id = partner.property_account_position and partner.property_account_position.id or False
                partner_id = partner.id
                addr = self.address_get(cr, uid, [partner_id], ['invoice'])
                if not addr.get('invoice', False):
                    raise osv.except_osv(_('Error!'),_("Partner doesn't have an address to make the invoice."))
            
                ref_type = 'bba'
                reference = invoice_obj.generate_bbacomm(cr, uid, ids, 'out_invoice', 'bba', partner_id, '', context={})
                referenc2 = reference['value']['reference']

                journal_obj = self.pool.get('account.journal')
                journal_id = journal_obj.search(cr, uid, [('code', '=', 'CUR')])
                if len(journal_id) == 0:
                    raise osv.except_osv(_('Error!'),_("Can't find required journal 'CUR'."))
                if len(journal_id) > 1:
                    raise osv.except_osv(_('Error!'),_("More than one journal 'CUR' found."))
                journal = journal_obj.browse(cr, uid, journal_id)[0]
                
                account_id = partner.property_account_receivable and partner.property_account_receivable.id or False
            
                datedue = datetime.date.today()
                invoice_id = invoice_obj.create(cr, uid, {
                    'journal_id': journal.id, 
                    'partner_id': partner_id,
                    'account_id': account_id,
                    'event_invoice': True,
                    'fiscal_position': fpos_id or False,
                    'reference_type': ref_type,
                    'type': 'out_invoice',
                    'reference': referenc2,
                    'date_due': datedue,
                    }, context=dict(context, no_store_function=True)) # Don't store function fields inside the loop.

                invoice_line_ids = []

                # event            
                line_value = invoice_line(amount)
                invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
                invoice_line_ids.append(invoice_line_id)

                # reduction
                reduction = datas.get('reduction',False)
                if reduction:
                    # reverse sign
                    line_value['quantity'] *= -1
                    line_value['price_unit'] = reduction
                    invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
                    invoice_line_ids.append(invoice_line_id)

                # options           
                def invoice_line_option(name,amount):
                    if name:
                        line_value = invoice_line(amount)
                        line_value['name'] = name
                        invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
                        invoice_line_ids.append(invoice_line_id)
                        
                invoice_line_option(datas.get('name_option1',False), datas.get('amount_option1',0.0))
                invoice_line_option(datas.get('name_option2',False), datas.get('amount_option2',0.0))
            
                # register event
                registration_id = register_event()        

                invoice_obj.write(cr, uid, [invoice_id], 
                                  {
                                   'invoice_line': [(6,0,invoice_line_ids)],
                                   'supplier_invoice_number': 'event_id={0}/reg_id={1}'.format(event_id,registration_id)
                                   }, context=context)
                invoice_id_list.append(invoice_id)
                invoice_obj.check_bba(cr, uid, invoice_id_list, context=context)

                invoice = invoice_obj.browse(cr, uid, invoice_id)
                # Create workflow
                invoice_obj.button_compute(cr, uid, invoice_id_list,{'type': 'out_invoice'}, set_total=True)
                wf_service = netsvc.LocalService('workflow')
                # Move to state 'open'
                wf_service.trg_validate(uid, 'account.invoice', invoice.id,'invoice_open', cr)
                            
        except:
            return {'id':0}
        else:
            return {
                'id':partner_id,
                'invoice_id':invoice_id,
                'reference':referenc2,
                'registration_id':registration_id
            }

    def create_web_registration(self,cr,uid,ids,vals,datas,context=None):        
        context = context or {}
        if ids == None:
            ids = []

        # if ids => no update res_partner, just use it to invoice
        # else create res_partner
        if not ids:
            ids.append(self.create(cr,uid,vals,context=context))            

        # get event product for natuurpunt CVN
        product_obj = self.pool.get('product.product')
        product_id = product_obj.search(cr, uid, [('event_product', '=', True)])
        assert(len(product_id) == 1)
        
        return self.create_event_invoice(cr,uid,ids,selected_product_id=product_id,datas=datas,context=context)

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
