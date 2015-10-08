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
from openerp import SUPERUSER_ID
from datetime import datetime
from datetime import time
from datetime import date
from mx import DateTime
import time
import logging
#import pdb

logger = logging.getLogger(__name__)

STATE = [
    ('none', 'Non Member'),
    ('canceled', 'Cancelled Member'),
    ('old', 'Old Member'),
    ('waiting', 'Waiting Member'),
    ('invoiced', 'Invoiced Member'),
    ('free', 'Free Member'),
    ('paid', 'Paid Member'),
    ('wait_member', 'Wachtend Lidmaatschap'), # pip = payment in process
]

STATE_F = [
    ('none', 'Geen lid'),
    ('canceled', 'Geannuleerd lid'),
    ('old', 'Oud lid'),
    ('waiting', 'Wachtend lid'),
    ('invoiced', 'Gefactureerd lid'),
    ('free', 'Gratis lid'),
    ('paid', 'Betaald lid'),
    ('wait_member', 'Wachtend Lidmaatschap'), # pip = payment in process
]

STATE_PRIOR = {
    'none': 0,
    'canceled': 1,
    'old': 2,
    'waiting': 3,
    'wait_member': 8,
    'invoiced': 5,
    'free': 6,
    'paid': 7,
}

class product_product(osv.osv):
    _inherit = 'product.product'
    
    _columns = {
		'included_product_ids': fields.many2many('product.product', 'product_included_product_rel', 'parent_product_id', 'child_product_id', 'Inbegrepen producten'),
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimensie 1', select=True),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimensie 2', select=True),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimensie 3', select=True),
        'membership_product': fields.boolean('Lidmaatschap'),
        'magazine_product': fields.boolean('Tijdschrift'),
    }
    
product_product()

class membership_third_payer_actions(osv.osv):
    _name = 'membership.third.payer.actions'

    _columns = {
		'partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'name': fields.char('Omschrijving', len=64),
        'amount': fields.float('Bedrag'),
        'date_from': fields.date('Datum vanaf'),
        'date_to': fields.date('Datum tot'),
    }

membership_third_payer_actions()

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def recalc_membership(self, cr, uid, partner_id, context=None):
        partner = self.pool.get('res.partner').browse(cr, uid, [partner_id], context=context)[0]

        membership_state_field = 'none'
        membership_start_date = None
        membership_stop_date = None
        membership_cancel_date = None
        membership_renewal_date = None
        membership_end_date = None

        update_partner = False

        if partner.free_member:
            membership_state_field = 'free'
        else:
            today = date.today()
            year_today = today.year

            sql_stat = '''select date_from, date_to, date_cancel, membership_cancel_id, membership_membership_line.state, npca_migrated, membership_renewal, date_invoice, sdd_mandate_id, sdd_mandate.state as mandate_state, website_payment, account_invoice.state as invoice_state, abo_company, company_deal, organisation_type_id, extract(year from date_from) as year_from, extract(year from date_to) as year_to, case when not(date_cancel IS NULL) and date_cancel < now() then 'canceled' else 'none' end as cancel_state
from membership_membership_line
inner join product_product on (product_product.id = membership_membership_line.membership_id and product_product.membership_product = True)
left outer join account_invoice_line on (account_invoice_line.id = account_invoice_line)
left outer join account_invoice on (account_invoice.id = invoice_id)
left outer join res_partner on (res_partner.id = account_invoice.partner_id)
left outer join sdd_mandate on (account_invoice.sdd_mandate_id = sdd_mandate.id)
where membership_membership_line.partner = %d
order by date_from, date_to
''' % (partner.id, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                date_from = sql_res['date_from']
                date_to = sql_res['date_to']
                date_cancel = sql_res['date_cancel']
                membership_cancel_id = sql_res['membership_cancel_id']
                state = sql_res['state']
                membership_renewal = sql_res['membership_renewal']
                date_invoice = sql_res['date_invoice']
                sdd_mandate_id = sql_res['sdd_mandate_id']
                mandate_state = sql_res['mandate_state']
                website_payment = sql_res['website_payment']
                invoice_state = sql_res['invoice_state']
                abo_company = sql_res['abo_company']
                company_deal = sql_res['company_deal']
                organisation_type_id = sql_res['organisation_type_id']
                year_from_membership = int(sql_res['year_from'])
                year_to_membership = int(sql_res['year_to'])
                cancel_state = sql_res['cancel_state']
                npca_migrated = sql_res['npca_migrated']

                if not membership_start_date:
                    membership_start_date = date_from
                membership_stop_date = date_to
                if membership_cancel_date:
                    if state == 'paid' or state == 'invoiced':
                        membership_cancel_date = None
                if date_cancel:
                    membership_cancel_date = date_cancel
                else:
                    if membership_cancel_id:
                        membership_cancel_date = date_to
                if membership_renewal:
                    membership_renewal_date = date_invoice
                if state == 'paid' or npca_migrated:
                    membership_end_date = date_to

                if state == 'canceled':
                    if date_cancel:
                        if cancel_state == 'canceled':
                            membership_state_field = 'canceled'
                    else:
                        membership_state_field = 'canceled'
                if state == 'paid':
                    if invoice_state == 'paid':
                        if year_to_membership == year_today or year_from_membership == year_today or (year_today > year_from_membership and year_today < year_to_membership):
                            membership_state_field = 'paid'
                        else:
                            if year_from_membership > year_today:
                                continue
                            else:
                                if year_to_membership < year_today:
                                    membership_state_field = 'old'
                    else:
                        if year_from_membership <= year_today:
                            if sdd_mandate_id and mandate_state == 'valid':
                                membership_state_field = 'invoiced'
                            elif website_payment:
                                membership_state_field = 'invoiced'
                            elif abo_company:
                                membership_state_field = 'invoiced'
                            elif company_deal:
                                membership_state_field = 'invoiced'
                            elif organisation_type_id and organisation_type_id == 1:
                                membership_state_field = 'invoiced'
                            elif invoice_state == 'draft' or invoice_state == 'proforma':
                                membership_state_field = 'waiting'
                            else:
                                membership_state_field = 'wait_member'
                            
                if state == 'invoiced' and year_from_membership <= year_today:
                    if sdd_mandate_id and mandate_state == 'valid':
                        membership_state_field = 'invoiced'
                    elif website_payment:
                        membership_state_field = 'invoiced'
                    elif abo_company:
                        membership_state_field = 'invoiced'
                    elif company_deal:
                        membership_state_field = 'invoiced'
                    elif organisation_type_id and organisation_type_id == 1:
                        membership_state_field = 'invoiced'
                    elif invoice_state == 'draft' or invoice_state == 'proforma':
                        membership_state_field = 'waiting'
                    else:
                        membership_state_field = 'wait_member'
                if state == 'waiting':
                    membership_state_field = 'waiting'

        if membership_state_field != partner.membership_state_b:
            update_partner = True
        if membership_start_date != partner.membership_start_b:
            update_partner = True
        if membership_stop_date != partner.membership_stop_b:
            update_partner = True
        if membership_cancel_date != partner.membership_cancel_b:
            update_partner = True
        if membership_renewal_date != partner.membership_renewal_date:
            update_partner = True
        if membership_end_date != partner.membership_end_b:
            update_partner = True

        if update_partner:
            vals = {
                'membership_state_b': membership_state_field,
                'membership_start_b': membership_start_date,
                'membership_stop_b': membership_stop_date,
                'membership_cancel_b': membership_cancel_date,
                'membership_renewal_date': membership_renewal_date,
                'membership_end_b': membership_end_date,
            }
            self.write(cr, uid, [partner.id], vals)
            cr.commit()
        return

    def _recalc_membership(self, cr, uid, context=None):
        logger.info('Calculation of partner membership data started')
        counter = 0
        counter1000 = 0
        partner_ids = self.search(cr, uid, ['|',('member_lines', '!=', False),('free_member', '=', True)], context=context)
        print 'Partners read'
        if partner_ids:
            for partner in partner_ids:
                self.recalc_membership(cr, uid, partner, context=context)
                counter = counter + 1
                counter1000 = counter1000 + 1
                if counter1000 == 1000:
                    print 'Partner memberships recalculated: ', counter
                    counter1000 = 0
        print 'Partner memberships recalculated: ', counter
        logger.info('Calculation of partner membership data ended')
        return True

    def onchange_free_member(self, cr, uid, ids, name, free_member, membership_nbr, context=None):
        res = {}
        if not ids:
            res['free_member'] = False
        else:
            if not membership_nbr:
                if free_member and name:
                    seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name','=','Lidnummer')])
                    membership_nbr = self.pool.get('ir.sequence').next_by_id(cr, uid, seq_id, context)
                    res['membership_nbr'] = membership_nbr
                    self.write(cr, uid, ids, {'membership_nbr':membership_nbr})
        return {'value':res}

    def _get_partner_id(self, cr, uid, ids, context=None):
        member_line_obj = self.pool.get('membership.membership_line')
        res_obj =  self.pool.get('res.partner')
        data_inv = member_line_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner.id)
        ids2 = list_partner
        while ids2:
            ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _get_invoice_partner(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        res_obj = self.pool.get('res.partner')
        data_inv = inv_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            if data.invoice_organisation:
                list_partner.append(data.membership_partner_id.id)
            else:
                list_partner.append(data.partner_id.id)
        ids2 = list_partner
        while ids2:
            ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            list_partner += ids2
        return list_partner

    def _membership_state(self, cr, uid, ids, name, args, context=None):
#        pdb.set_trace()
        print 'CALC MEMBERSHIP STATE', name, ids
        print 'ARGS:',args
        print 'CONTEXT:',context
        if context:
            if 'type' in context or not ('lang' in context):
                return {}
# following line is to prevent update of standard membership_state field when creating a new invoice from the bank statement pop-up screen
            if 'default_orig_name_save' in context:
                return {}
            if 'default_invoice_id' in context:
                return{}
            if 'skip_write' in context:
                return {}
            if 'mandate_id' in context:
                return {}
            if 'from_refund' in context:
                return {}
        else:
            return {}
        """This Function return Membership State For Given Partner.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Partner IDs
        @param name: Field Name
        @param context: A standard dictionary for contextual values
        @param return: Dictionary of Membership state Value
        """
        res = {}
        for id in ids:
            res[id] = 'none'
        today = time.strftime('%Y-%m-%d')
        for id in ids:
            if 1 == 1:
                if name == 'membership_state':
                    continue
            partner_data = self.browse(cr, SUPERUSER_ID, id, context=context)
            s = 4
            if partner_data.membership_cancel and today > partner_data.membership_cancel:
                res[id] = 'canceled'
                s = 2
            if partner_data.membership_stop and today > partner_data.membership_stop:
                res[id] = 'old'
                s = 5
            if partner_data.member_lines:
                for mline in partner_data.member_lines:
                    if mline.date_from > today:
                        continue
                    if mline.account_invoice_line.product_id and mline.account_invoice_line.product_id.membership_product == False:
                        continue
                    if mline.npca_migrated and s == 4 and mline.date_to >= today:
                        if mline.membership_cancel_id:
                            s = 2
                        else:
                            s = 0
                    elif mline.date_to >= today: #end_membership:
                        if mline.account_invoice_line and mline.account_invoice_line.invoice_id:
                            mstate = mline.account_invoice_line.invoice_id.state
                            if mstate == 'paid' or mline.account_invoice_line.invoice_id.amount_total == 0.00:
                                s = 0
                                inv = mline.account_invoice_line.invoice_id
                                for payment in inv.payment_ids:
                                    if payment.invoice.type == 'out_refund':
                                        s = 2
#                                break
                            elif mline.account_invoice_line.invoice_id.definitive_reject:
                                s = 3
                            elif mstate == 'open' and s!=0 and mline.account_invoice_line.invoice_id.sdd_mandate_id and mline.account_invoice_line.invoice_id.sdd_mandate_id.state == 'valid':
                                s = 1
                            elif mstate == 'open' and s!=0 and mline.account_invoice_line.invoice_id.website_payment:
                                s = 1
                            elif mstate == 'open' and s!=0 and mline.account_invoice_line.invoice_id.partner_id.abo_company:
                                s = 1
                            elif mstate == 'open' and s!=0 and mline.account_invoice_line.invoice_id.partner_id.company_deal:
                                s = 1
                            elif mstate == 'open' and s!=0 and mline.account_invoice_line.invoice_id.partner_id.organisation_type_id.id == 1:
                                s = 1
                            elif mstate == 'open' and s!=0 and s!=1:
                                s = 8
                            elif mstate == 'cancel' and s!=0 and s!=1 and s!=8:
                                s = 2
                            elif (mstate == 'draft' or mstate == 'proforma') and s!=0 and s!=1 and s!=8:
                                s = 3
                               
                if s==4:
                    for mline in partner_data.member_lines:
                        if mline.account_invoice_line and mline.account_invoice_line.product_id.membership_product and mline.date_from < today and mline.date_to < today and mline.date_from <= mline.date_to and (mline.account_invoice_line and mline.account_invoice_line.invoice_id.state) == 'paid':
                            s = 5
                        else:
                            s = 6
                print "S:",s
                if s==0:
                    res[id] = 'paid'
                elif s==1:
                    res[id] = 'invoiced'
                elif s==2:
                    res[id] = 'canceled'
                elif s==3:
                    res[id] = 'waiting'
                elif s==5:
                    res[id] = 'old'
                elif s==6:
                    res[id] = 'none'
                elif s==8:
                    res[id] = 'wait_member'
            if partner_data.free_member and s!=0:
                res[id] = 'free'
#            if partner_data.associate_member:
#                res_state = self._membership_state(cr, uid, [partner_data.associate_member.id], name, args, context=context)
#                res[id] = res_state[partner_data.associate_member.id]
        return res

    def _membership_date(self, cr, uid, ids, name, args, context=None):
        print 'CALC MEMBERSHIP DATE:', name
        if not ('lang' in context):
            return {}
        """Return  date of membership"""
        name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
            partner_id = partner.id
            res[partner.id] = {
                 'membership_start': False,
                 'membership_stop': False,
                 'membership_end': False,
                 'membership_cancel': False
            }
            if name == 'membership_start':
                line_id = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner_id),('membership_id.membership_product', '=', True)],
                            limit=1, order='date_from', context=context)
                if line_id:
                        res[partner.id]['membership_start'] = member_line_obj.read(cr, SUPERUSER_ID, line_id[0], ['date_from'], context=context)['date_from']

            if name == 'membership_stop':
                line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner_id),('membership_id.membership_product', '=', True)],
                            limit=1, order='date_to desc', context=context)
                if line_id1:
                      res[partner.id]['membership_stop'] = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']

            if name == 'membership_end':
                line_id3 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner_id),('membership_id.membership_product', '=', True),('state','=','paid')],
                            limit=1, order='date_to desc', context=context)
                if line_id3:
                      res[partner.id]['membership_end'] = member_line_obj.read(cr, SUPERUSER_ID, line_id3[0], ['date_to'], context=context)['date_to']

            if name == 'membership_cancel':
                if partner.membership_state == 'canceled':
                    line_id2 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True)], limit=1, order='date_cancel', context=context)
                    if line_id2:
                        res[partner.id]['membership_cancel'] = member_line_obj.read(cr, SUPERUSER_ID, line_id2[0], ['date_cancel'], context=context)['date_cancel']
        return res

    def _membership_start_date(self, cr, uid, ids, name, args, context=None):
        if 1 == 1:
            if name == 'membership_start':
                return {}
        """Return  date of membership"""
        name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
            line_id = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True)],
                            limit=1, order='date_from', context=context)
            if line_id:
                res[partner.id] = member_line_obj.read(cr, SUPERUSER_ID, line_id[0], ['date_from'], context=context)['date_from']
        return res
    def _membership_stop_date(self, cr, uid, ids, name, args, context=None):
        if 1 == 1:
            if name == 'membership_stop':
                return {}
        """Return  date of membership"""
        name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
            line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True)],
                            limit=1, order='date_to desc', context=context)
            if line_id1:
                res[partner.id] = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']
        return res
    def _membership_end_date(self, cr, uid, ids, name, args, context=None):
        if 1 == 1:
            if name == 'membership_end':
                return {}
        """Return  date of membership"""
        name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
            line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True),('state','=','paid')],
                            limit=1, order='date_to desc', context=context)
            if line_id1:
                res[partner.id] = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']
        return res
    def _membership_cancel_date(self, cr, uid, ids, name, args, context=None):
        if 1 == 1:
            if name == 'membership_cancel':
                return {}
        """Return  date of membership"""
        name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
            line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True),('state','=','canceled')],
                            limit=1, order='date_cancel desc', context=context)
            if line_id1:
                cancel_date = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']
                if partner.membership_end_f > cancel_date:
                    res[partner.id] = None
                else:
                    res[partner.id] = cancel_date
        return res

    def _get_partners(self, cr, uid, ids, context=None):
        ids2 = ids
        while ids2:
            ids2 = self.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            ids += ids2
        return ids

    def __get_membership_state(self, *args, **kwargs):
        return self._membership_state(*args, **kwargs)

    _columns = {
        'third_payer_flag': fields.boolean('3de Betaler'),
        'third_payer_one_time': fields.boolean('Eenmalige 3de Betaler'),
        'third_payer_amount': fields.float('Bedrag'),
		'third_payer_id': fields.many2one('res.partner', '3de Betaler Id', select=True),
		'third_payer_action_ids': fields.one2many('membership.third.payer.actions', 'partner_id', '3de Betaler Acties'),
        'third_payer_invoice': fields.boolean('Factuur 3de Betaler'),
        'third_payer_processed': fields.boolean('3de Betaler Verwerkt'),
        'abo_company': fields.boolean('Abonnementfirma'),
        'company_deal': fields.boolean('Bedrijfsdeal'),
		'membership_renewal_product_id': fields.many2one('product.product', 'Product Hernieuwing Lidmaatschap', select=True),
		'free_membership_class_id': fields.many2one('res.partner.free.class', 'Gratis Lid Categorie', select=True),
        'membership_state_b': fields.selection([('none', 'Geen lid'),('canceled', 'Geannuleerd lid'),('old', 'Oud lid'),('waiting', 'Wachtend lid'),('invoiced', 'Gefactureerd lid'),('free', 'Gratis lid'),('paid', 'Betaald lid'),('wait_member', 'Wachtend lidmaatschap')], string='Lidmaatschapsstatus (B)'),
        'membership_state_f': fields.function(_membership_state, string='Lidmaatschapsstatus (F)', type='selection', selection=STATE_F),
        'membership_state': fields.function(
#                    __get_membership_state,
                    _membership_state,
                    string = 'Current Membership Status', type = 'selection',
                    selection = STATE,
#
                    store = False),
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (_get_partners, ['free_member', 'membership_state', 'associate_member'], 10)
#                    }, help="""It indicates the membership state.
#                    -Non Member: A partner who has not applied for any membership.
#                    -Cancelled Member: A member who has cancelled his membership.
#                    -Old Member: A member whose membership date has expired.
#                    -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
#                    -Invoiced Member: A member whose invoice has been created.
#                    -Paying member: A member who has paid the membership fee."""),
        'membership_start_b': fields.date('Lidmaatschap startdatum (B)'),
        'membership_start_f': fields.function(_membership_start_date, string='Lidmaatschap startdatum (F)', type='date'),
        'membership_start': fields.function(
                    _membership_start_date, 
                    string = 'Membership Start Date', type = 'date',
#
                    store = False),
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10, ),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member', 'membership_state'], 10)
#                    }, help="Date from which membership becomes active."),
        'membership_stop_b': fields.date('Lidmaatschap einddatum (B)'),
        'membership_stop_f': fields.function(_membership_stop_date, string='Lidmaatschap einddatum (F)', type='date'),
        'membership_stop': fields.function(
                    _membership_stop_date,
                    string = 'Membership End Date', type='date',
#
                    store = False),
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member', 'membership_state'], 10)
#                    }, help="Date until which membership remains active."),
        'membership_cancel_b': fields.date('Lidmaatschap annulatiedatum (B)'),
        'membership_cancel_f': fields.function(_membership_cancel_date, string='Lidmaatschap annulatiedatum (F)', type='date'),
        'membership_cancel': fields.function(
                    _membership_cancel_date,
                    string = 'Cancel Membership Date', type='date',
#
                    store = False),
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 11),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member', 'membership_state'], 10)
#                    }, help="Date on which membership has been cancelled"),
        'free_member_comment': fields.char('Reden gratis lid'),
        'membership_renewal_date': fields.date('Lidmaatschap hernieuwingsdatum (B)'),
        'membership_end_b': fields.date('Lidmaatschap recentste einddatum (B)'),
        'membership_end_f': fields.function(_membership_end_date, string='Lidmaatschap recentste einddatum (F)', type='date'),
        'membership_end': fields.function(
                    _membership_end_date, 
                    string = 'Recentste einddatum lidmaatschap', type='date',
#
                    store = False),
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member', 'membership_state'], 10)
#                    }, help="Date until which membership remains active."),
        'lid': fields.boolean('Lid'),
        'focus': fields.boolean('Focus'),
        'oriolus': fields.boolean('Oriolus'),
    }

    _default = {
        'membership_state_field': 'none',
    }

res_partner()

class membership_cancel_reason(osv.osv):
    _name = 'membership.cancel.reason'

    _columns = {
        'name': fields.char('Name', len=64, select=True),
        'ref': fields.char('Code', len=32),
    }

membership_cancel_reason()

class membership_membership_line(osv.osv):
    _inherit = 'membership.membership_line'

    def onchange_cancel(self, cr, uid, ids, membership_cancel_id, date_cancel, context=None):
        res = {}
        if membership_cancel_id:
            if not date_cancel:
                res['date_cancel'] = datetime.today().strftime('%Y-12-31')
        return {'value':res}

    def _function_payment_method(self, cr, SUPERUSER_ID, ids, name, arg, context=None):
        res = {}
        for member in self.browse(cr, 1, ids):
            if member.account_invoice_id:
#                 sql_stat = "select case when sdd_mandate_id IS NULL then 'Overschrijving' else 'Domiciliëring' end as type from account_invoice where id = %s" % (member.account_invoice_id.id, )
#                 cr.execute(sql_stat)
#                 sql_res = cr.dictfetchone()
#                 if sql_res and sql_res['type']:
#                     res[member.id] = sql_res['type']
#                 else:
#                     res[member.id] = ''
                if member.account_invoice_id.sdd_mandate_id and member.account_invoice_id.sdd_mandate_id == 'valid':
                    res[member.id] = 'Domiciliëring'
                else:
                    if member.account_invoice_id.payment_ids:
                        for payment in member.account_invoice_id.payment_ids:
                            res[member.id] = payment.journal_id.code + ' ' + payment.journal_id.name
                    else:
                        res[member.id] = 'Overschrijving'
            else:
                res[member.id] = 'Migratie'
        return res

    def _get_partners(self, cr, uid, ids, context=None):
        list_membership_line = []
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.pool.get('res.partner').browse(cr, uid, ids, context=context):
            if partner.member_lines:
                list_membership_line += member_line_obj.search(cr, uid, [('id', 'in', [ l.id for l in partner.member_lines])], context=context)
        return list_membership_line

    def _get_membership_lines(self, cr, uid, ids, context=None):
        list_membership_line = []
        member_line_obj = self.pool.get('membership.membership_line')
        for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
            if invoice.invoice_line:
                list_membership_line += member_line_obj.search(cr, uid, [('account_invoice_line', 'in', [ l.id for l in invoice.invoice_line])], context=context)
        return list_membership_line

    def _state(self, cr, uid, ids, name, args, context=None):
        """Compute the state lines
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Membership Line IDs
        @param name: Field Name
        @param context: A standard dictionary for contextual values
        @param return: Dictionary of state Value
        """
        res = {}
        inv_obj = self.pool.get('account.invoice')
        for line in self.browse(cr, SUPERUSER_ID, ids, context=context):
            if line.npca_migrated:
                if line.membership_cancel_id:
                    res[line.id] = 'canceled'
                else:
                    res[line.id] = 'paid'
            else:
                cr.execute('''
                SELECT i.state, i.id FROM
                account_invoice i
                WHERE
                i.id = (
                    SELECT l.invoice_id FROM
                    account_invoice_line l WHERE
                    l.id = (
                        SELECT  ml.account_invoice_line FROM
                        membership_membership_line ml WHERE
                        ml.id = %s
                        )
                    )
                ''', (line.id,))
                fetched = cr.fetchone()
                if not fetched:
                    res[line.id] = 'canceled'
                    continue
                istate = fetched[0]
                state = 'none'
                if (istate == 'draft') | (istate == 'proforma'):
                    state = 'waiting'
                elif istate == 'open':
                    state = 'invoiced'
                elif istate == 'paid':
                    state = 'paid'
                    inv = inv_obj.browse(cr, SUPERUSER_ID, fetched[1], context=context)
                    for payment in inv.payment_ids:
                        if payment.invoice and payment.invoice.type == 'out_refund':
                            state = 'canceled'
                elif istate == 'cancel':
                    state = 'canceled'
                res[line.id] = state
        return res

    _columns = {
		'membership_cancel_id': fields.many2one('membership.cancel.reason', 'Reden Stopzetting', select=True),
		'npca_migrated': fields.boolean('Gemigreerd uit NPCA'),
        'remarks': fields.char('Opmerkingen'),
        'payment_method': fields.function(_function_payment_method, string='Betaalwijze', type='char'),
        'state': fields.function(_state,
                        string='Membership Status', type='selection',
                        selection=STATE, store = {
                        'account.invoice': (_get_membership_lines, ['state'], 10),
                        'res.partner': (_get_partners, ['membership_state_b'], 12),
                        }, help="""It indicates the membership status.
                        -Non Member: A member who has not applied for any membership.
                        -Cancelled Member: A member who has cancelled his membership.
                        -Old Member: A member whose membership date has expired.
                        -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
                        -Invoiced Member: A member whose invoice has been created.
                        -Paid Member: A member who has paid the membership amount."""),
    }

membership_membership_line()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def create(self, cr, uid, vals, context=None):
        if 'membership_invoice' in vals and vals['membership_invoice']:
            journal_obj = self.pool.get('account.journal')
            journal_id = journal_obj.search(cr, uid, [('code', '=', 'LID')])
            if journal_id and len(journal_id) > 0:
        	    vals['journal_id'] = journal_id[0]
        res = super(account_invoice, self).create(cr, uid, vals, context=context)
        inv = self.browse(cr, uid, res)
        if (inv.partner_id or inv.membership_partner_id) and inv.membership_invoice:
            if inv.membership_partner_id and not inv.membership_partner_id.membership_nbr:
                partner_obj = self.pool.get('res.partner')
                seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name','=','Lidnummer')])
                membership_nbr = self.pool.get('ir.sequence').next_by_id(cr, uid, seq_id, context)
                partner_obj.write(cr, uid, [inv.membership_partner_id.id], {'membership_nbr':membership_nbr})
            else:
                if not inv.partner_id.membership_nbr:
                    partner_obj = self.pool.get('res.partner')
                    seq_id = self.pool.get('ir.sequence').search(cr, uid, [('name','=','Lidnummer')])
                    membership_nbr = self.pool.get('ir.sequence').next_by_id(cr, uid, seq_id, context)
                    partner_obj.write(cr, uid, [inv.partner_id.id], {'membership_nbr':membership_nbr})
        return res

    _columns = {
		'website_payment': fields.boolean('Betaling via Website',),
        'membership_invoice': fields.boolean('Lidmaatschapsfactuur'),
        'definitive_reject': fields.boolean('Definitive Reject'),
    }

account_invoice()

class res_partner_free_class(osv.osv):
    _name = 'res.partner.free.class'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
    }

res_partner_free_class()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
