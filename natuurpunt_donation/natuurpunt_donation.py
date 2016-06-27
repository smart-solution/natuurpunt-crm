# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from datetime import datetime
from datetime import time
from datetime import date
from dateutil.relativedelta import relativedelta
from mx import DateTime
import time
import logging

logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _inherit = 'product.product'
    
    _columns = {
        'donation_product': fields.boolean('Gift'),
    }
    
product_product()

class donation_cancel_reason(osv.osv):
    _name = 'donation.cancel.reason'

    _columns = {
        'name': fields.char('Name', len=64, select=True),
        'ref': fields.char('Code', len=32),
    }

donation_cancel_reason()

class donation_partner_account(osv.osv):

    _name = 'donation.partner.account'

    def onchange_analacct(self, cr, uid, ids, analytic_account_id, product_id, context=None):
        res = {}
        if not product_id:
	        prod_obj = self.pool.get('product.product')
	        prod_ids = prod_obj.search(cr, uid, [('donation_product','=',True)])
	        if len(prod_ids) == 1:
		        prod = prod_obj.browse(cr, uid, prod_ids[0])
                res['product_id'] = prod.id
	
        return {'value':res}

    _columns = {
	'partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', select=True),
        'donation_amount': fields.float('Gift Bedrag'),
        'donation_start': fields.date('Startdatum Gift'),
        'donation_end': fields.date('Einddatum Gift'),
        'donation_cancel': fields.date('Annulatie Gift'),
        'cancel_reason_id': fields.many2one('donation.cancel.reason', 'Reden Annulatie', select=True),
        'interval_type': fields.selection((('J','Jaar'),('M','Maand'),('W','Week'),('D','Dag')), 'Interval Type'),
        'interval_number': fields.integer('Interval Aantal'),
        'last_invoice_date': fields.date('Datum Laatste Facturatie'),
        'next_invoice_date': fields.date('Datum Volgende Facturatie'),
        'product_id': fields.many2one('product.product', 'Product', select=True),
    }

    _defaults = {
        'interval_number': 1,
    }

    def write(self, cr, uid, ids, vals, context=None):
        if 'donation_cancel' in vals and vals['donation_cancel']:
            vals['next_invoice_date'] = False
        return super(donation_partner_account, self).write(cr, uid, ids, vals=vals, context=context)

    def _create_donation_invoices(self, cr, uid, context=None):
        logger.info('Searching for donations that must be invoiced')
        date_invoice = datetime.today()
        donation_ids = self.search(cr, uid, [
            '|',
            ('next_invoice_date', '=', False),
            ('next_invoice_date', '<=', date_invoice),
            ('donation_start', '<=', date_invoice),
            ('donation_cancel', '=', False),
            ], context=context)
        if donation_ids:
            logger.info('Found %s donation invoices to create'%(len(donation_ids)))
            self.create_donation_invoice(cr, uid, donation_ids, product_id=None, datas=None, context=context)
        else:
            logger.info('0 donation invoices created')
        return True

    def create_donation_invoice(self, cr, uid, ids, product_id=None, datas=None, context=None):
        start_time = time.time()
        id_list = []

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_tax_obj = self.pool.get('account.invoice.tax')
        partner_obj = self.pool.get('res.partner')
        journal_obj = self.pool.get('account.journal')
        donation_line_obj = self.pool.get('donation.donation.line')

        invoice_list = []
        for donation in self.browse(cr, uid, ids, context=context):
            logger.info('DONATION ID: %s'%(donation.id))
            logger.info('DONATION PARTNER ID: %s'%(donation.partner_id.id))
            if context == None:
                context = {}
                context['uid'] = 1
                context['tz'] = 'Europe/Brussels'
                context['lang'] = 'en_US'
                context['active_model'] = 'donation.partner.account'
            context['active_ids'] = [donation.id]
            context['active_id'] = donation.id
            
            product_id = donation.product_id.id
            partner_id = donation.partner_id.id
            company_id = donation.product_id.company_id.id
            analytic_account_id = donation.analytic_account_id.id
            journal_id = None
            journals = journal_obj.search(cr, uid, [('code','=','GIFT')], context=context)
            if journals:
                for journal in journal_obj.browse(cr, uid, journals, context=context):
                    journal_id = journal.id

            analytic_dimension_1_id = None
            analytic_dimension_2_id = None
            analytic_dimension_3_id = None
            if donation.analytic_account_id.dimension_id.sequence == 1:
                analytic_dimension_1_id = donation.analytic_account_id.id
                if donation.analytic_account_id.default_dimension_2_id:
                    analytic_dimension_2_id = donation.analytic_account_id.default_dimension_2_id.id
                if donation.analytic_account_id.default_dimension_3_id:
                    analytic_dimension_3_id = donation.analytic_account_id.default_dimension_3_id.id
            if donation.analytic_account_id.dimension_id.sequence == 2:
                analytic_dimension_2_id = donation.analytic_account_id.id
                if donation.analytic_account_id.default_dimension_1_id:
                    analytic_dimension_1_id = donation.analytic_account_id.default_dimension_1_id.id
                if donation.analytic_account_id.default_dimension_3_id:
                    analytic_dimension_3_id = donation.analytic_account_id.default_dimension_3_id.id
            if donation.analytic_account_id.dimension_id.sequence == 3:
                analytic_dimension_3_id = donation.analytic_account_id.id
                if donation.analytic_account_id.default_dimension_1_id:
                    analytic_dimension_1_id = donation.analytic_account_id.default_dimension_1_id.id
                if donation.analytic_account_id.default_dimension_2_id:
                    analytic_dimension_2_id = donation.analytic_account_id.default_dimension_2_id.id

            amount_inv = donation.donation_amount

            account_id = donation.partner_id.property_account_receivable and donation.partner_id.property_account_receivable.id or False
            fpos_id = donation.partner_id.property_account_position and donation.partner_id.property_account_position.id or False
            addr = partner_obj.address_get(cr, uid, [donation.partner_id.id], ['invoice'])
            if not addr.get('invoice', False):
                raise osv.except_osv(_('Error!'),
                        _("Partner doesn't have an address to make the invoice."))

            quantity = 1

            line_value =  {
                'product_id': product_id,
            }

            payment_term_id = None
            mandate_id = None
            partner_bank_id = None
            sql_stat = '''select sdd_mandate.id as mandate_id, account_payment_term.id as payment_term_id, res_partner_bank.id as partner_bank_id from res_partner, res_partner_bank, sdd_mandate, account_payment_term
where res_partner.id = res_partner_bank.partner_id
  and partner_bank_id = res_partner_bank.id
  and sdd_mandate.state = 'valid'
  and account_payment_term.name = 'Direct debit'
  and res_partner.id = %d
order by res_partner_bank.sequence''' % (partner_id, )
            cr.execute(sql_stat)
            sql_res = cr.dictfetchone()
            if sql_res and sql_res['payment_term_id']:
                payment_term_id = sql_res['payment_term_id']
                mandate_id = sql_res['mandate_id']
                partner_bank_id = sql_res['partner_bank_id']

            if not mandate_id == None:   
                line_dict = invoice_line_obj.product_id_change(cr, uid, {}, product_id, False, quantity, '', 'out_invoice', partner_id, fpos_id, price_unit=amount_inv, context=context)
                line_value.update(line_dict['value'])
                line_value['price_unit'] = amount_inv
                if line_value.get('invoice_line_tax_id', False):
                    tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                    line_value['invoice_line_tax_id'] = tax_tab
                line_value['analytic_dimension_1_id'] = analytic_dimension_1_id
                line_value['analytic_dimension_2_id'] = analytic_dimension_2_id
                line_value['analytic_dimension_3_id'] = analytic_dimension_3_id

                ref_type = 'bba'
                reference = invoice_obj.generate_bbacomm(cr, uid, ids, 'out_invoice', 'bba', partner_id, '', context={})
                referenc2 = reference['value']['reference']

                today = datetime.today()
                datedue = datetime.today() + relativedelta(days=30)
                period_id =  self.pool.get('account.period').find(cr, uid, today)

                invoice_id = invoice_obj.create(cr, uid, {
                    'partner_id': partner_id,
                    'account_id': account_id,
                    'donation_invoice': True,
                    'fiscal_position': fpos_id or False,
                    'payment_term': payment_term_id,
                    'sdd_mandate_id': mandate_id,
                    'partner_bank_id': partner_bank_id,
                    'reference_type': ref_type,
                    'type': 'out_invoice',
                    'reference': referenc2,
                    'date_due': datedue,
                    'date_invoice': today,
                    'donation_id': donation.id,
                    'company_id': company_id,
                    'journal_id': journal_id,
                    'period_id': period_id and period_id[0] or False
    #                'invoice_line': [(0, 0, line_value)],
                    }, context=dict(context, no_store_function=True)) # Don't store function fields inside the loop.

                invoice_list = []
                line_value['invoice_id'] = invoice_id
                invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=dict(context, no_store_function=True))
                invoice_obj.write(cr, uid, invoice_id, {'invoice_line': [(6, 0, [invoice_line_id])]}, context=context)
                invoice_list.append(invoice_id)

                invoice_obj.check_bba(cr, uid, invoice_list, context=context)
                wf_service = netsvc.LocalService('workflow')
                wf_service.trg_validate(uid, 'account.invoice', invoice_id, 'invoice_open', cr) 

                if donation.interval_type == 'D':
                    next_invoice_date = datetime.today() + relativedelta(days=donation.interval_number)
                if donation.interval_type == 'W':
                    next_invoice_date = datetime.today() + relativedelta(weeks=donation.interval_number)
                if donation.interval_type == 'M':
                    next_invoice_date = datetime.today() + relativedelta(months=donation.interval_number)
                if donation.interval_type == 'J':
                    next_invoice_date = datetime.today() + relativedelta(years=donation.interval_number)

                last_invoice_date = datetime.today().strftime('%Y-%m-%d')

                # Do not set a next invoice date if after the end date
                if donation.donation_end and time.strftim(donation.donation_end, '%Y%') <= last_invoice_date:
                    self.write(cr, uid, donation.id, {'last_invoice_date': last_invoice_date, 'next_invoice_date': False}, context=context)
                else:
                    self.write(cr, uid, donation.id, {'last_invoice_date': last_invoice_date, 'next_invoice_date': next_invoice_date}, context=context)

                donation_line_id = donation_line_obj.create(cr, uid, {
                    'partner_id': partner_id,
                    'invoice_id': invoice_id,
                    'donation_id': donation.id,
                    'date_invoice': today,
                    'amount_total': amount_inv,
                    'analytic_account_id': analytic_account_id,
                    }, context=context) # Don't store function fields inside the loop.

        # Code lifted from orm.py to store function fields outside the loop which
        # is a lot more performant than in every create.
        result = []
        cols = [
            'partner_id',
            'account_id',
            'donation_invoice',
            'fiscal_position',
            'payment_term',
            'sdd_mandate_id',
            'partner_bank_id',
            'reference_type',
            'type',
            'reference',
            'date_due',
            'invoice_line',
        ]
        result += invoice_obj._store_get_values(cr, uid, invoice_list,
            list(set(cols + invoice_obj._inherits.values())),
            context)
        result.sort()
        done = []
        for order, object, some_ids, fields2 in result:
            if not (object, some_ids, fields2) in done:
                self.pool.get(object)._store_set_values(cr, uid, some_ids, fields2, context)
                done.append((object, some_ids, fields2))

        # End of runction field storage. Restart loop, but this time over the invoices instead of partners.
        for invoice in invoice_obj.browse(cr, uid, invoice_list, context=context):
            values = {}
            amount = invoice_obj.action_date_get(cr, uid, [invoice_id], None)
            if amount:
                values.update(amount)

donation_partner_account()

class donation_donation_line(osv.osv):
    _name = 'donation.donation.line'

    _columns = {
		'partner_id': fields.many2one('res.partner', 'Partner', select=True),
		'invoice_id': fields.many2one('account.invoice', 'Factuur', select=True),
		'donation_id': fields.many2one('donation.partner.account', 'Gift', select=True),
	    'date_invoice': fields.date('Datum Factuur'),
	    'amount_total': fields.float('Bedrag'),
	    'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', select=True),
            'state': fields.related('invoice_id', 'state', string='State', type='char'),
    }

    _order = 'date_invoice desc'

donation_donation_line()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
        'donation_invoice': fields.boolean('Giftfactuur'),
        'donation_id': fields.many2one('donation.partner.account', 'Gift', select=True),
    }

account_invoice()

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'donation_ids': fields.one2many('donation.partner.account', 'partner_id', 'Giften'),
        #'donation_line_ids': fields.one2many('donation.donation.line', 'partner_id', 'Giftfacturen', domain=[('state','in',('draft','open','paid'))]),
        # performance issue revert - fix todo
        'donation_line_ids': fields.one2many('donation.donation.line', 'partner_id', 'Giftfacturen'),
    }

res_partner()

class payment_order(osv.osv):
    _inherit = 'payment.order'

    def button_add_sdd_invoices(self, cr, uid, ids, context=None):
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','sdd.add.payment'), ('name','=','natuurpunt.sdd.add.payment.view')])

        order = self.browse(cr, uid, ids)[0]
        if order.id:
            context['default_payment_order_id'] = order.id
            context['default_due_date'] = datetime.today().strftime('%Y-%m-%d')
    
            return {
                'type': 'ir.actions.act_window',
                'name': 'Toevoegen SDD facturen',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view_id[0],
                'res_model': 'sdd.add.payment',
                'target': 'new',
                'context': context,
                }

payment_order()

class sdd_add_payment(osv.osv_memory):
    _name = 'sdd.add.payment'

    _columns = {
        'payment_order_id': fields.many2one('payment.order', 'Payment order', select=True),
        'due_date': fields.date('Vervaldag'),
        'membership_new': fields.boolean('Nieuwe lidmaatschappen'),
        'membership_renewal': fields.boolean('Hernieuwingen'),
        'donation': fields.boolean('Giften'),
    }

    def add_invoices(self, cr, uid, ids, context=None):
        res = {}
        order_line_obj = self.pool.get('payment.line')
        move_obj = self.pool.get('account.move.line')

        counter = 0
        counter1000 = 0

# ,('invoice_line_id.invoice_id.payment_ids','=',False)
        for order in self.browse(cr, uid, ids, context):
            if order.membership_new:
                move_ids = move_obj.search(cr, uid, [('invoice_line_id.invoice_id.membership_invoice', '=', True),('invoice_line_id.invoice_id.membership_renewal','=',False),('invoice_line_id.invoice_id.sdd_mandate_id','!=',False),('invoice_line_id.invoice_id.sdd_mandate_id.state','=','valid'),('reconcile_id','=',False),('statement_id','=',False),('invoice.type','=','out_invoice'),('invoice.state','=','open')])
                comm = 'Lidmaatschap'
            else:
                if order.membership_renewal:
                    move_ids = move_obj.search(cr, uid, [('invoice_line_id.invoice_id.membership_invoice', '=', True),('invoice_line_id.invoice_id.membership_renewal','=',True),('invoice_line_id.invoice_id.sdd_mandate_id','!=',False),('invoice_line_id.invoice_id.sdd_mandate_id.state','=','valid'),('reconcile_id','=',False),('statement_id','=',False),('invoice.type','=','out_invoice'),('invoice.state','=','open')])
                    comm = 'Lidmaatschap'
                else:
                    if order.donation:
                        move_ids = move_obj.search(cr, uid, [('invoice_line_id.invoice_id.donation_invoice', '=', True),('invoice_line_id.invoice_id.sdd_mandate_id','!=',False),('invoice_line_id.invoice_id.sdd_mandate_id.state','=','valid'),('reconcile_id','=',False),('statement_id','=',False),('invoice.type','=','out_invoice'),('invoice.state','=','open')])
                        comm = 'Gift'

            line2bank = move_obj.line2bank(cr, uid, move_ids, None, context)

            for line in move_obj.browse(cr, uid, move_ids, context):
                if line.amount_to_pay > 0.00 and counter < 10000:
                    if order.payment_order_id.date_prefered == "now":
                        #no payment date => immediate payment
                        date_to_pay = False
                    elif order.payment_order_id.date_prefered == 'due':
                        date_to_pay = line.date_maturity
                    elif order.payment_order_id.date_prefered == 'fixed':
                        date_to_pay = order.payment_order_id.date_scheduled
                    order_line_obj.create(cr, uid,{
                            'move_line_id': line.id,
                            'amount_currency': line.amount_to_pay,
                            'bank_id': line2bank.get(line.id),
                            'order_id': order.payment_order_id.id,
                            'partner_id': line.partner_id and line.partner_id.id or False,
                            'communication': line.ref or '/',
                            'state': line.invoice and line.invoice.reference_type != 'none' and 'structured' or 'normal',
                            'date': date_to_pay,
                            'currency': (line.invoice and line.invoice.currency_id.id) or line.journal_id.currency.id or line.journal_id.company_id.currency_id.id,
                        }, context=context)
                    counter += 1
                    counter1000 += 1
#                    if counter1000 == 1000:
#                        logger.info('Nbr of lines added to payment order: ',counter)

        return {'type':'ir.actions.act_window_close','context': context,}

    def onchange_payment_type(self, cr, uid, ids, payment, membership_new, membership_renewal, donation, context=None):
        res = {}
        if payment == 'new' and membership_new:
            res['membership_new'] = True
            res['membership_renewal'] = False
            res['donation'] = False
        else:
            if payment == 'renewal' and membership_renewal:
                res['membership_renewal'] = True
                res['membership_new'] = False
                res['donation'] = False
            else:
                if payment == 'donation' and donation:
                    res['donation'] = True
                    res['membership_new'] = False
                    res['membership_renewal'] = False
	
        return {'value':res}

sdd_add_payment()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
