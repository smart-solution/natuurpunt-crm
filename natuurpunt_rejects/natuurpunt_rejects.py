# -*- encoding: utf-8 -*-

import datetime
from mx import DateTime
import time

from osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _

class sdd_reject_code(osv.osv):
    _name = 'sdd.reject.code'

    _columns = {
        'ref': fields.char('Code'),
        'name': fields.char('Omschrijving'),
        'immediate_reject': fields.boolean('Onmiddelijke weigering'),
    }

sdd_reject_code()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'sdd_reject_count': fields.integer('Aantal weigeringen'),
        'sdd_reject1_id': fields.many2one('sdd.reject.code', 'Weigeringscode 1', select=True),
        'sdd_reject2_id': fields.many2one('sdd.reject.code', 'Weigeringscode 2', select=True),
        'sdd_reject3_id': fields.many2one('sdd.reject.code', 'Weigeringscode 3', select=True),
        'sdd_reject1_date': fields.date('Datum weigering 1'),
        'sdd_reject2_date': fields.date('Datum weigering 2'),
        'sdd_reject3_date': fields.date('Datum weigering 3'),
        'sdd_reject1_bankstmt_id': fields.many2one('account.bank.statement', 'Rekeninguitreksel 1', select=True),
        'sdd_reject2_bankstmt_id': fields.many2one('account.bank.statement', 'Rekeninguitreksel 2', select=True),
        'sdd_reject3_bankstmt_id': fields.many2one('account.bank.statement', 'Rekeninguitreksel 3', select=True),
    }

    _defaults = {
        'sdd_reject_count': 0,
    }

account_invoice()

class account_move_line(osv.osv):

    _inherit = 'account.move.line'

    _columns = {
        'reject_date': fields.date('Weigering Datum'),
    }

    def fields_get(self, cr, user, allfields=None, context=None, write_access=True):
        """
        work-a-round for process_rejects -> copy account_move
        don't copy one2may field entry_ids. It points to the same model
        and this will create a query that kills performance
        """
        res = super(account_move_line, self).fields_get(cr,user,allfields=allfields,context=context,write_access=write_access)
        if context and 'reject' in context:
            if 'entry_ids' in res:
                del res['entry_ids']
        return res

    def copy_data(self, cr, uid, id, default=None, context=None):
        """
        work-a-round for process_rejects -> copy account_move
        don't copy one2may field entry_ids. It points to the same model
        and this will create a query that kills performance
        happens also in a read of this field. Skipping is not a good fix
        but a work-a-round
        """
        if context and 'reject' in context:
            if default is None:
                default = {}
            default['entry_ids'] = []
        return super(account_move_line, self).copy_data(cr,uid,id,default=default,context=context)

class account_bank_statement(osv.osv):

    _inherit = 'account.bank.statement'

    _columns = {
        'reject_processed': fields.boolean('Rejects Processed')
    }

    def create_refund(self, cr, uid, ids, mode='cancel', context=None):
        refund_wiz = self.pool.get('account.invoice.refund')
        vals={}
        vals['filter_refund'] = mode
        vals['description'] = context['reject_code']
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('code','=','LIDC')])
        if not journal_ids or len(journal_ids) > 1:
            raise osv.except_osv(_('Error!'), _('No refund journal could be found.'))
        vals['journal_id'] = journal_ids[0]
        vals['date'] = time.strftime('%Y-%m-%d')
        vals['period'] = self.pool.get('account.period').find(cr, uid, dt=vals['date'], context=context)[0]

        wiz_id = self.pool.get('account.invoice.refund').create(cr, uid, vals, context=context)

        context['skip_write'] = True
        refund_res = self.pool.get('account.invoice.refund').compute_refund(cr, uid, [wiz_id], mode=mode, context=context)

        return refund_res
    
    def process_rejects(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        payment_line_obj = self.pool.get('payment.line')
        reject_code_obj = self.pool.get('sdd.reject.code')
        move_line_obj = self.pool.get('account.move.line')
        move_obj = self.pool.get('account.move')
        partner_obj = self.pool.get('res.partner')

        for stmt in self.browse(cr, uid, ids):
            for reject in stmt.sdd_ref_ids:
                if reject.reason and reject.partner_id and not stmt.reject_processed:
                    reject_code = None
                    reject_code_ids = reject_code_obj.search(cr, uid,[('ref','=',reject.reason)])
                    if reject_code_ids:
                        reject_code = reject_code_ids[0]
                    immediate_reject = False
                    sql_stat = "select immediate_reject from sdd_reject_code where id = %d" % (reject_code, )
                    cr.execute(sql_stat)
                    sql_res = cr.dictfetchone()
                    if sql_res:
                        immediate_reject = sql_res['immediate_reject']

                    payment_line_id = None
                    invoice_id = None
                    sdd_reject_count = 0
                    payment_line_id = None
                    move_id = None
                    move_cancel_id = None
                    reconcile_id = None

                    sql_stat = "select payment_line.id as payment_line_id, account_invoice.id as invoice_id, account_invoice.sdd_reject_count, account_move.id as move_id from payment_line, account_move_line, account_move, account_invoice where payment_line.partner_id = %d and payment_line.sdd_mandate_id = %d and rtrim(upper(payment_line.communication)) = rtrim(upper('%s')) and payment_line.move_line_id = account_move_line.id and account_move_line.move_id = account_move.id and account_move.name = account_invoice.number order by account_invoice.id desc limit 1" % (reject.partner_id.id, reject.sdd_mandate_id.id, reject.comm, )
                    cr.execute(sql_stat)
                    sql_res = cr.dictfetchone()
                    if sql_res:
                        payment_line_id = sql_res['payment_line_id']
                        invoice_id = sql_res['invoice_id']
                        sdd_reject_count = sql_res['sdd_reject_count']
                        move_id = sql_res['move_id']

                    if move_id:
                        sql_stat = "select reconcile_id from account_move_line where move_id = %d and not(reconcile_id IS NULL)" % (move_id, )
                        cr.execute(sql_stat)
                        sql_res = cr.dictfetchone()
                        if sql_res:
                            reconcile_id = sql_res['reconcile_id']


                    if payment_line_id:
                        sql_stat = "delete from payment_line where id = %d" % (payment_line_id, )
                        cr.execute(sql_stat)

                    if invoice_id:
                        if sdd_reject_count == 0:
                            invoice_obj.write(cr, uid, invoice_id, {'sdd_reject_count': 1, 'sdd_reject1_id': reject_code, 'sdd_reject1_date': stmt.date, 'sdd_reject1_bankstmt_id': stmt.id}, context=context)
                        if sdd_reject_count == 1:
                            invoice_obj.write(cr, uid, invoice_id, {'sdd_reject_count': 2, 'sdd_reject2_id': reject_code, 'sdd_reject2_date': stmt.date, 'sdd_reject2_bankstmt_id': stmt.id}, context=context)
                        if sdd_reject_count == 2 or immediate_reject:
                            invoice_obj.write(cr, uid, invoice_id,
                                              {'definitive_reject': True,
                                               'sdd_reject_count': 3,
                                               'sdd_reject3_id': reject_code,
                                               'sdd_reject3_date': stmt.date,
                                               'sdd_reject3_bankstmt_id': stmt.id},
                                              context=context)
                            self.pool.get('sdd.mandate').write(cr, uid , [reject.sdd_mandate_id.id], {'state':'cancel'})

                    if reconcile_id:
                        move_line_ids = move_line_obj.search(cr, uid,[('reconcile_id','=',reconcile_id)])
                        move_line_obj._remove_move_reconcile(cr, uid, move_line_ids, False, context=context)
                        for line in move_line_obj.browse(cr, uid, move_line_ids):
                            if line.move_id.id != move_id:
                                move_cancel_id = line.move_id.id

                    if move_cancel_id:
                        context['reject'] = True
                        dupl_id = move_obj.copy(cr, uid, move_cancel_id, context=context)
                        move_obj.button_cancel(cr, uid, [dupl_id], context=context)
                        dupl_line_ids = move_line_obj.search(cr, uid,[('move_id','=',dupl_id)])
                        for dupl_line in move_line_obj.browse(cr, uid, dupl_line_ids):
                            debit = dupl_line.credit
                            credit = dupl_line.debit
                            sql_stat = 'update account_move_line set debit = {:.2f}, credit = {:.2f} where id = {}'.format(debit, credit, dupl_line.id)
                            cr.execute(sql_stat)
                        move_obj.button_validate(cr, uid, [dupl_id], context=context)
                        reconcile_ids = []
                        for line in move_line_obj.browse(cr, uid, dupl_line_ids):
                            if line.account_id.reconcile:
                                reconcile_ids.append(line.id)
                        move_line_ids = move_line_obj.search(cr, uid,[('move_id','=',move_cancel_id)])
                        for line in move_line_obj.browse(cr, uid, move_line_ids):
                            if line.account_id.reconcile:
                                reconcile_ids.append(line.id)
                        move_line_obj.reconcile(cr, uid, reconcile_ids, 'auto', False, False, False, context=context)

                        move_line_obj.write(cr, uid, reconcile_ids, {'reject_date':datetime.datetime.today().strftime('%Y-%m-%d')})

            self.write(cr, uid, [stmt.id], {'reject_processed':True})

        return True

account_bank_statement()

