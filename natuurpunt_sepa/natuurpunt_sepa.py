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
from openerp.osv import orm
#import datetime
from mx import DateTime
import time
import re
from openerp.tools.translate import _
from openerp import netsvc
from datetime import datetime
from openerp.tools import float_compare
from openerp.report import report_sxw
from itertools import groupby
import openerp.addons.decimal_precision as dp
import logging

logger = logging.getLogger(__name__)


# Some monkey-patching to get rid of the inefficient standard implementation
from openerp.addons.l10n_be_invoice_bba.invoice import account_invoice as aiv
from openerp.addons.account.account_invoice import account_invoice as aiv2

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
        'membership_invoice': fields.boolean('Lidmaatschapsfactuur'),
        'third_payer_amount': fields.float('Bedrag'),
		'third_payer_id': fields.many2one('res.partner', '3de Betaler Id', select=True),
		'membership_partner_id': fields.many2one('res.partner', '3de Betaler Id', select=True),
        'invoice_organisation': fields.boolean('Betaald aan Afdeling'),
        'membership_renewal': fields.boolean('Hernieuwingsfactuur'),
    }

    def invoice_validate(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids):
            if invoice.membership_invoice and invoice.amount_total == 0.0:
                self.write(cr, uid, [invoice.id], {'state':'paid'})
                #self.pool.get('account.move').unlink(cr, 1, [invoice.move_id.id])
                ids.remove(invoice.id)
        return super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        if 'membership_invoice' in vals and vals['membership_invoice']:
            vals['account_id'] = 4114
        if 'donation_invoice' in vals and vals['donation_invoice']:
            vals['account_id'] = 4204

        return super(account_invoice, self).create(cr, uid, vals, context=context)

    def check_bba(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids, context):
            same_ids = self.search(cr, uid,
                            [('id', '!=', inv.id), ('type', '=', 'out_invoice'),
                             ('reference_type', '=', 'bba'), ('reference', '=', inv.reference), ('company_id', '=', inv.company_id.id)])
            if same_ids:
                raise osv.except_osv(_('Warning!'),
                    _('The BBA Structured Communication has already been used!' \
                      '\nPlease create manually a unique BBA Structured Communication.'))

    def validate_crm_payment(self, cr, uid, ids, context=None):
        mv_obj = self.pool.get('account.move')
        mv_line_obj = self.pool.get('account.move.line')
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.state == 'open':
                if 'web' in context:
                        jrn_obj = self.pool.get('account.journal')
                        jrn_ids = jrn_obj.search(cr, uid, [('code','=','OGON')])
                        jrn = jrn_obj.browse(cr, uid, jrn_ids[0])
                        ogone_log_obj = self.pool.get('ogone.log')
                        ogone_ids = ogone_log_obj(cr ,uid, [('invoice_id','=',invoice.id)])
                        ogone_log_obj.write(cr, uid, ogone_ids, {'state':'paid'}, context=context)
                else:
                    if invoice.membership_invoice:
                            jrn_obj = self.pool.get('account.journal')
                            jrn_ids = jrn_obj.search(cr, uid, [('code','=','DOML')])
                            jrn = jrn_obj.browse(cr, uid, jrn_ids[0])
                    else:
                            jrn_obj = self.pool.get('account.journal')
                            jrn_ids = jrn_obj.search(cr, uid, [('code','=','DOMG')])
                            jrn = jrn_obj.browse(cr, uid, jrn_ids[0])

                mv_vals = {
                    'journal_id': jrn.id,
                    'date': datetime.today(),
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
                    'account_id': invoice.account_id.id,
                    'credit': invoice.residual,
                    'quantity': 1,
                }
                credit_mv_line_id = mv_line_obj.create(cr, uid, credit_mv_line_vals)
                
                # Post the journal entry
                mv_obj.button_validate(cr, uid, [mv_id], context=context)
                logger.info('Direct Debit move validated')

                # Find the invoice move line to reconcile
                rec_line_id = False
                for line in invoice.move_id.line_id:
                    if line.account_id == invoice.account_id:
                        rec_line_id = line.id
                # If no recociliation account could be found
                if not rec_line_id:
                    raise osv.except_osv(_('Error!'), _('No recociliation account could be found for the journal entry: %s'%(invoice.move_id.name)))

                reconcile_ids = [credit_mv_line_id, rec_line_id]

                # Reconcile the journal entry
                #mv_line_obj.reconcile(cr, uid, reconcile_ids, 'auto', invoice.account_id.id, mv.period_id.id, mv.journal_id.id, context=context)
                try: 
                    mv_line_obj.reconcile(cr, uid, reconcile_ids, 'auto', False, False, False, context=context)
                except osv.except_osv, exc:
                    args = exc.args
                    reconcile_details = _('invoice:{}, partner:{}, ids:{}'.format(invoice.number, invoice.partner_id.id, reconcile_ids)) 
                    except_osv_message = args[1] + ' ' + reconcile_details if args[1] else reconcile_details
                    raise osv.except_osv(args[0],except_osv_message) 

                logger.info('Diret Debit Invoice Reconciliation done')

account_invoice()

# This one is like the write() in l10n_be_invoice_bba, but the check
# can be skipped by passing 'skip_check_bba' in the context. The BBA check
# can then be performed separately after all writes have been done via the newly
# added check_bba method, see in the class below.
def write_aiv(self, cr, uid, ids, vals, context=None):
    if isinstance(ids, (int, long)):
        ids = [ids]
    ids_to_check = []
    for inv in self.browse(cr, uid, ids, context):
        if vals.has_key('reference_type'):
            reference_type = vals['reference_type']
        else:
            reference_type = inv.reference_type or ''
        if reference_type == 'bba':
            if vals.has_key('reference'):
                bbacomm = vals['reference']
            else:
                bbacomm = inv.reference or ''
            if self.check_bbacomm(bbacomm):
                reference = re.sub('\D', '', bbacomm)
                ref = '+++' + reference[0:3] + '/' + reference[3:7] + '/' + reference[7:] + '+++'
                if ref != inv.reference:
                    vals['reference'] = ref
                    if context and not context.get('skip_check_bba'):
                        ids_to_check.append(inv.id)
    res = super(aiv, self).write(cr, uid, ids, vals, context)

    for inv in self.browse(cr, uid, ids_to_check, context):
        same_ids = self.search(cr, uid,
                        [('id', '!=', inv.id), ('type', '=', 'out_invoice'),
                         ('reference_type', '=', 'bba'), ('reference', '=', inv.reference), ('company_id', '=', inv.company_id.id)])
        if same_ids:
            raise osv.except_osv(_('Warning!'),
                _('The BBA Structured Communication has already been used!' \
                  '\nPlease create manually a unique BBA Structured Communication.'))
    #self.check_bba(cr, uid, ids_to_check, context=context)
    return res 

aiv.write = write_aiv

# This one is a copy of action_move_create in the account_invoice module. It's
# been improved to perform only one write as opposed to potentially two in the
# original implementation.
def action_move_create_aiv(self, cr, uid, ids, context=None):
    """Creates invoice related analytics and financial move lines"""
    ait_obj = self.pool.get('account.invoice.tax')
    cur_obj = self.pool.get('res.currency')
    period_obj = self.pool.get('account.period')
    payment_term_obj = self.pool.get('account.payment.term')
    journal_obj = self.pool.get('account.journal')
    move_obj = self.pool.get('account.move')
    if context is None:
        context = {}
    inv_date = {}
    for inv in self.browse(cr, uid, ids, context=context):
        if not inv.journal_id.sequence_id:
            raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
        if not inv.invoice_line:
            raise osv.except_osv(_('No Invoice Lines!'), _('Please create some invoice lines.'))
        if inv.move_id:
            continue

        ctx = context.copy()
        ctx.update({'lang': inv.partner_id.lang})
        if not inv.date_invoice:
            inv_date = {'date_invoice': fields.date.context_today(self,cr,uid,context=context)}
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
        # create the analytical lines
        # one move line per invoice line
        iml = self._get_analytic_lines(cr, uid, inv.id, context=ctx)
        # check if taxes are all computed
        compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
        self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

        # I disabled the check_total feature
        group_check_total_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'group_supplier_inv_check_total')[1]
        group_check_total = self.pool.get('res.groups').browse(cr, uid, group_check_total_id, context=context)
        if group_check_total and uid in [x.id for x in group_check_total.users]:
            if (inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0)):
                raise osv.except_osv(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

        if inv.payment_term:
            total_fixed = total_percent = 0
            for line in inv.payment_term.line_ids:
                if line.value == 'fixed':
                    total_fixed += line.value_amount
                if line.value == 'procent':
                    total_percent += line.value_amount
            total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
            if (total_fixed + total_percent) > 100:
                raise osv.except_osv(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

        # one move line per tax line
        iml += ait_obj.move_line_get(cr, uid, inv.id)

        entry_type = ''
        if inv.type in ('in_invoice', 'in_refund'):
            ref = inv.reference
            entry_type = 'journal_pur_voucher'
            if inv.type == 'in_refund':
                entry_type = 'cont_voucher'
        else:
            ref = self._convert_ref(cr, uid, inv.number)
            entry_type = 'journal_sale_vou'
            if inv.type == 'out_refund':
                entry_type = 'cont_voucher'

        diff_currency_p = inv.currency_id.id <> company_currency
        # create one move line for the total and possibly adjust the other lines amount
        total = 0
        total_currency = 0
        total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml, context=ctx)
        acc_id = inv.account_id.id

        name = inv['name'] or inv['supplier_invoice_number'] or '/'
        totlines = False
        if inv.payment_term:
            totlines = payment_term_obj.compute(cr,
                    uid, inv.payment_term.id, total, inv.date_invoice or False, context=ctx)
        if totlines:
            res_amount_currency = total_currency
            i = 0
            ctx.update({'date': inv.date_invoice})
            for t in totlines:
                if inv.currency_id.id != company_currency:
                    amount_currency = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, t[1], context=ctx)
                else:
                    amount_currency = False

                # last line add the diff
                res_amount_currency -= amount_currency or 0
                i += 1
                if i == len(totlines):
                    amount_currency += res_amount_currency

                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': t[1],
                    'account_id': acc_id,
                    'date_maturity': t[0],
                    'amount_currency': diff_currency_p \
                            and amount_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref,
                })
        else:
            iml.append({
                'type': 'dest',
                'name': name,
                'price': total,
                'account_id': acc_id,
                'date_maturity': inv.date_due or False,
                'amount_currency': diff_currency_p \
                        and total_currency or False,
                'currency_id': diff_currency_p \
                        and inv.currency_id.id or False,
                'ref': ref
        })

        date = inv.date_invoice or time.strftime('%Y-%m-%d')

        part = self.pool.get("res.partner")._find_accounting_partner(inv.partner_id)

        line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part.id, date, context=ctx)),iml)

        line = self.group_lines(cr, uid, iml, line, inv)

        journal_id = inv.journal_id.id
        journal = journal_obj.browse(cr, uid, journal_id, context=ctx)
        if journal.centralisation:
            raise osv.except_osv(_('User Error!'),
                    _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

        line = self.finalize_invoice_move_lines(cr, uid, inv, line)

        move = {
            'ref': inv.reference and inv.reference or inv.name,
            'line_id': line,
            'journal_id': journal_id,
            'date': date,
            'narration': inv.comment,
            'company_id': inv.company_id.id,
        }
        period_id = inv.period_id and inv.period_id.id or False
        ctx.update(company_id=inv.company_id.id,
                   account_period_prefer_normal=True)
        if not period_id:
            period_ids = period_obj.find(cr, uid, inv.date_invoice, context=ctx)
            period_id = period_ids and period_ids[0] or False
        if period_id:
            move['period_id'] = period_id
            for i in line:
                i[2]['period_id'] = period_id

        ctx.update(invoice=inv)
        move_id = move_obj.create(cr, uid, move, context=ctx)
        new_move_name = move_obj.browse(cr, uid, move_id, context=ctx).name
        # make the invoice point to that move
        vals = inv_date
        vals.update({'move_id': move_id,'period_id':period_id, 'move_name':new_move_name})
        self.write(cr, uid, [inv.id], vals, context=ctx)
        # Pass invoice in context in method post: used if you want to get the same
        # account move reference when creating the same invoice after a cancelled one:
        move_obj.post(cr, uid, [move_id], context=ctx)
    self._log_event(cr, uid, ids)
    return True

aiv2.action_move_create = action_move_create_aiv


class account_journal(osv.osv):
    _inherit = 'account.journal'

    _columns = {
		'membership_account_id': fields.many2one('account.account', 'Lidmaatschap Te Ontvangen', select=True),
    }

account_journal()

class membership_membership_line(osv.osv):
    _inherit = 'membership.membership_line'

    def create(self, cr, uid, vals, context=None):
        invoice_line_obj = self.pool.get('account.invoice.line')
        invline = invoice_line_obj.browse(cr, uid, vals['account_invoice_line'])
        vals['partner'] = invline.invoice_id.membership_partner_id.id
        return super(membership_membership_line, self).create(cr, uid, vals, context=context)

membership_membership_line()

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def create_membership_invoice(self, cr, uid, ids, selected_product_id=None, datas=None, context=None):
        start_time = time.time()
        id_list = []
        if 'sdd_mandate_bank_partner_view' in context:
            for id in ids:
                sql_stat = '''select partner_id from res_partner_bank where id = %d''' % (context['default_partner_bank_id'], )
                cr.execute(sql_stat)
                sql_res = cr.dictfetchone()
                if sql_res and sql_res['partner_id']:
                    id_list.append(sql_res['partner_id'])
        else:
            for id in ids:
                id_list.append(id)

        """ Create Customer Invoice of Membership for partners.
        @param datas: datas has dictionary value which consist Id of Membership product and Cost Amount of Membership.
                      datas = {'membership_product_id': None, 'amount': None}
        """

        invoice_obj = self.pool.get('account.invoice')
        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_tax_obj = self.pool.get('account.invoice.tax')

        selected_product_id = selected_product_id or datas.get('membership_product_id', False)
        analytic_dimension_1_id = None
        analytic_dimension_2_id = None
        analytic_dimension_3_id = None
        sql_stat = '''select analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id from product_product
where id = %s''' % (selected_product_id, )
        cr.execute(sql_stat)
        sql_res = cr.dictfetchone()
        if sql_res and sql_res['analytic_dimension_1_id']:
            analytic_dimension_1_id = sql_res['analytic_dimension_1_id']
            analytic_dimension_2_id = sql_res['analytic_dimension_2_id']
            analytic_dimension_3_id = sql_res['analytic_dimension_3_id']

        invoice_organisation = datas.get('invoice_organisation', False)
        recruiting_organisation_id = datas.get('recruiting_organisation_id', False)
        membership_renewal = datas.get('membership_renewal', False)

        amount = datas.get('amount', 0.0)
        invoice_list = []
        if type(ids) in (int, long,):
            ids = [ids]
        for partner in self.browse(cr, uid, id_list, context=context):
            if recruiting_organisation_id:
                sql_stat = 'update res_partner set recruiting_organisation_id = %d where id = %d' % (recruiting_organisation_id, partner.id,)
                cr.execute(sql_stat)

            account_id = partner.property_account_receivable and partner.property_account_receivable.id or False
            fpos_id = partner.property_account_position and partner.property_account_position.id or False
            addr = self.address_get(cr, uid, [partner.id], ['invoice'])
            if not addr.get('invoice', False):
                raise osv.except_osv(_('Error!'),
                        _("Partner doesn't have an address to make the invoice."))
            quantity = 1

            product_id = selected_product_id or datas.get('membership_product_id', False)
            if membership_renewal and partner.membership_renewal_product_id:
                product_id = partner.membership_renewal_product_id.id
                amount_to_inv = partner.membership_renewal_product_id.list_price
            else:
                amount_to_inv = amount
            line_value =  {
                'product_id': product_id,
            }

            membership_product = partner.membership_renewal_product_id and partner.membership_renewal_product_id.id or False

            third_payer_id = None
            third_payer_amount = 0.00
            third_payer_invoice = False
            third_payer_one_time = False
            third_payer_processed = False
            sql_stat = '''select p1.third_payer_id, p2.third_payer_amount, p1.third_payer_invoice, p2.third_payer_one_time, p1.third_payer_processed from res_partner p1, res_partner p2
where p1.id = %d
  and p1.third_payer_id = p2.id
  and (p1.third_payer_processed = False or p1.third_payer_processed IS NULL or p2.third_payer_one_time = False or p2.third_payer_one_time IS NULL)''' % (partner.id, )
            cr.execute(sql_stat)
            sql_res = cr.dictfetchone()
            print 'SQL RES:',sql_res
            if sql_res and sql_res['third_payer_id'] and sql_res['third_payer_amount']:
                third_payer_id = sql_res['third_payer_id']
                third_payer_amount = sql_res['third_payer_amount']
                third_payer_invoice = sql_res['third_payer_invoice']
                third_payer_one_time = sql_res['third_payer_one_time']
                third_payer_processed = sql_res['third_payer_processed']
            if third_payer_id and third_payer_amount == 0.00 and not(third_payer_invoice):
                sql_stat = '''select amount from membership_third_payer_actions where partner_id = %d and date_from <= cast(now() as date) and date_to >= cast(now() as date)''' % (third_payer_id, )
                cr.execute(sql_stat)
                sql_res = cr.dictfetchone()
                print 'SQL RES2:',sql_res
                if sql_res and sql_res['amount']:
                    third_payer_amount = sql_res['amount']
            if third_payer_invoice:
                partner_id = third_payer_id
                third_payer_amount = 0.00
            else:
                partner_id = partner.id

            payment_term_id = None
            mandate_id = None
            partner_bank_id = None
            sql_stat = '''select sdd_mandate.id as mandate_id, account_payment_term.id as payment_term_id, res_partner_bank.id as partner_bank_id from res_partner, res_partner_bank, sdd_mandate, account_payment_term
where res_partner.id = res_partner_bank.partner_id
  and partner_bank_id = res_partner_bank.id
  and sdd_mandate.state = 'valid'
  and account_payment_term.name = 'Direct debit'
  and res_partner.id = %d''' % (partner.id, )
            cr.execute(sql_stat)
            sql_res = cr.dictfetchone()
            if sql_res and sql_res['payment_term_id']:
                payment_term_id = sql_res['payment_term_id']
                mandate_id = sql_res['mandate_id']
                partner_bank_id = sql_res['partner_bank_id']
            amount_inv = amount_to_inv - third_payer_amount
            
            inv_org = False
            if invoice_organisation:
                if recruiting_organisation_id:
                    partner_id = recruiting_organisation_id
                    inv_org = True
                else:
                    if partner.recruiting_organisation_id:
                        partner_id = partner.recruiting_organisation_id.id
                        inv_org = True

            line_dict = invoice_line_obj.product_id_change(cr, uid, {},
                            product_id, False, quantity, '', 'out_invoice', partner.id, fpos_id, price_unit=amount_inv, context=context)
            line_value.update(line_dict['value'])
            line_value['price_unit'] = amount_inv
            if line_value.get('invoice_line_tax_id', False):
                tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                line_value['invoice_line_tax_id'] = tax_tab
            line_value['analytic_dimension_1_id'] = analytic_dimension_1_id
            line_value['analytic_dimension_2_id'] = analytic_dimension_2_id
            line_value['analytic_dimension_3_id'] = analytic_dimension_3_id

            if inv_org:
                ref_type = 'none'
                referenc2 = '[%d] %s' % (partner.id, partner.name, )
            else:
                ref_type = 'bba'
                reference = invoice_obj.generate_bbacomm(cr, uid, ids, 'out_invoice', 'bba', partner_id, '', context={})
                referenc2 = reference['value']['reference']

            today = datetime.today()
#            days30 = datetime.timedelta(days=30)
#            datedue = today + days30
            datedue = today

            invoice_id = invoice_obj.create(cr, uid, {
                'partner_id': partner_id,
                'membership_partner_id': partner.id,
                'account_id': account_id,
                'membership_invoice': True,
                'website_payment': True if ('web' in context) else False,
                'third_payer_id': third_payer_id,
                'third_payer_amount': third_payer_amount,
                'fiscal_position': fpos_id or False,
                'payment_term': payment_term_id,
                'sdd_mandate_id': mandate_id,
                'partner_bank_id': partner_bank_id,
                'reference_type': ref_type,
                'type': 'out_invoice',
                'reference': referenc2,
                'date_due': datedue,
                'invoice_organisation': invoice_organisation,
                'membership_renewal': membership_renewal,
                }, context=dict(context, no_store_function=True)) # Don't store function fields inside the loop.

            line_value['invoice_id'] = invoice_id
            invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
            invoice_obj.write(cr, uid, invoice_id, {'invoice_line': [(6, 0, [invoice_line_id])]}, context=context)
            invoice_list.append(invoice_id)

            invoice_obj.check_bba(cr, uid, invoice_list, context=context)
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid, 'account.invoice', invoice_id, 'invoice_open', cr) 
            cr.commit()
 
        # Code lifted from orm.py to store function fields outside the loop which
        # is a lot more performant than in every create.
        result = []
        cols = [
            'partner_id',
            'membership_partner_id',
            'account_id',
            'membership_invoice',
            'website_payment',
            'third_payer_id',
            'third_payer_amount',
            'fiscal_position',
            'payment_term',
            'sdd_mandate_id',
            'partner_bank_id',
            'reference_type',
            'type',
            'reference',
            'date_due',
            'invoice_organisation',
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

            if third_payer_one_time:
                sql_stat = '''update res_partner set third_payer_processed = True where id = %d''' % (invoice.partner_id.id, )
                cr.execute(sql_stat)
            """
            renewal_prod_id = self._np_membership_renewal_product(cr, uid, invoice.partner_id, context=context)
            if renewal_prod_id:
                sql_stat = '''update res_partner set membership_renewal_product_id = %d where id = %d''' % (renewal_prod_id[0], invoice.partner_id.id, )
            else:
                sql_stat = '''update res_partner set membership_renewal_product_id = %d where id = %d''' % (product_id, invoice.partner_id.id, )
            """
            sql_stat = '''update res_partner set membership_renewal_product_id = %d where id = %d''' % (product_id, invoice.partner_id.id, )
            cr.execute(sql_stat)

            values = {}
            amount = invoice_obj.action_date_get(cr, uid, [invoice_id], None)
            if amount:
                values.update(amount)

        return invoice_list

res_partner()

class membership_invoice(osv.osv_memory):
    _inherit = "membership.invoice"

    _columns = {
        'invoice_organisation': fields.boolean('Betaald aan Afdeling'),
		'recruiting_organisation_id': fields.many2one('res.partner', 'Wervende Organisatie', select=True),
        'membership_renewal': fields.boolean('Hernieuwingsfactuur'),
    }

    def membership_invoice(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        partner_obj = self.pool.get('res.partner')
        datas = {}
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)
        if data:
            data = data[0]
            datas = {
                'membership_product_id': data.product_id.id,
                'amount': data.member_price,
                'invoice_organisation': data.invoice_organisation,
                'recruiting_organisation_id': data.recruiting_organisation_id.id,
                'membership_renewal': data.membership_renewal,
            }
        invoice_list = partner_obj.create_membership_invoice(cr, uid, context.get('active_ids', []), datas=datas, context=context)

        try:
            search_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')[1]
        except ValueError:
            search_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')[1]
        except ValueError:
            form_view_id = False

        return  {
            'domain': [('id', 'in', invoice_list)],
            'name': 'Membership Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_id, 'form')],
            'search_view_id': search_view_id,
        }

membership_invoice()


class banking_export_sdd_wizard(orm.TransientModel):
    _inherit = 'banking.export.sdd.wizard'

    def save_sepa(self, cr, uid, ids, context=None):
        '''
        Save the SEPA Direct Debit file: mark all payments in the file
        as 'sent'. Write 'last debit date' on mandate and set oneoff
        mandate to expired
        '''
        sepa_export = self.browse(cr, uid, ids[0], context=context)
        print '**************************'
        print 'SEPA IDS:', ids
        print '**************************'
        if sepa_export.file_id:
            self.pool.get('banking.export.sdd').write(
                cr, uid, sepa_export.file_id.id, {'state': 'sent'},
                context=context)
        wf_service = netsvc.LocalService('workflow')
        for order in sepa_export.payment_order_ids:
            to_expire_ids = []
            first_mandate_ids = []

            line_nbr = len(order.line_ids)                
            for line in order.line_ids:
                if line.sdd_mandate_id.type == 'oneoff':
                    to_expire_ids.append(line.sdd_mandate_id.id)
                elif line.sdd_mandate_id.type == 'recurrent':
                    seq_type = line.sdd_mandate_id.recurrent_sequence_type
                    if seq_type == 'final':
                        to_expire_ids.append(line.sdd_mandate_id.id)
                    elif seq_type == 'first':
                        first_mandate_ids.append(line.sdd_mandate_id.id)

                if line.ml_inv_ref:
                    print "invoice %s status: %s"%(line.ml_inv_ref.number,line.ml_inv_ref.state)
                    if line.ml_inv_ref.state == 'open':
                        inv = self.pool.get('account.invoice').validate_crm_payment(cr, uid, [line.ml_inv_ref.id], context=context)
                    else:
                        logger.info('Invoice %s is already paid'%(line.ml_inv_ref.number))

                    line_nbr = line_nbr - 1
                    #if line_nbr == 80:
                    #    raise osv.except_osv(_('Error!'), _('Krash!'))
                    cr.commit()

                    logger.info('Direct Debit Order invoice preocessed : %s'%(line.ml_inv_ref.number))
                logger.info('Direct Debit Order lines left to process : %s'%(line_nbr))

            self.pool['sdd.mandate'].write(
                cr, uid, to_expire_ids, {'state': 'expired'}, context=context)
            self.pool['sdd.mandate'].write(
                cr, uid, first_mandate_ids, {
                    'recurrent_sequence_type': 'recurring',
                    'sepa_migrated': True,
                }, context=context)

            mandate_ids = [line.sdd_mandate_id.id for line in order.line_ids]
            unique_mandate_ids = [k for k, _ in groupby(sorted(mandate_ids, key=lambda x: mandate_ids.index(x)))]
            self.pool['sdd.mandate'].write(
                cr, uid, unique_mandate_ids,
                {'last_debit_date': datetime.today().strftime('%Y-%m-%d')},
                context=context)
            wf_service.trg_validate(uid, 'payment.order', order.id, 'done', cr)

            logger.info('Direct Debit Order processed')

        return {'type': 'ir.actions.act_window_close'}

banking_export_sdd_wizard()

class ogone_log(osv.osv):
    _name = 'ogone.log'

    _columns = {
        'invoice_id': fields.many2one('account.invoice', 'Invoice', select=True),
        'date_created': fields.date('Creation date', select=True),
        'state': fields.selection([('open','Open'),
                                   ('paid', 'Paid')],
                                   'Status',
                                   help='When OGONE payment is created the status will be \'Open\'.\n'
                                        'And the website processes the OGONE request it changes to the \'Paid\' status.'),
    }

    _defaults = {
        'state': 'open',
    }

ogone_log()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
