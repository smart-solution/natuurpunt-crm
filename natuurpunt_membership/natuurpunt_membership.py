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
from functools import partial
from natuurpunt_tools import get_included_product_ids

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

def recursive_flatten_list(baselist, cmplist, func):
    if cmplist:
        return recursive_flatten_list([func(element,cmplist[0][index]) for index,element in enumerate(baselist)], cmplist[1:], func)
    else:
        return baselist

def compose(*functions):
    return reduce(lambda f, g: lambda x: g(f(x)), functions, lambda x: x)

def split_memberships_and_magazines(prod_object, cr, uid, prod_id):
    if prod_id:
        is_membership_prod = lambda prod_id : prod_object.search(cr, uid, [('id','=',prod_id),('membership_product','=',True)])
        membership_prod_ids = is_membership_prod(prod_id)
        is_magazine_prod = lambda prod_id : prod_object.search(cr, uid, [('id','=',prod_id),('magazine_product','=',True)])
        magazine_prod_ids = is_magazine_prod(prod_id)
        return (membership_prod_ids,magazine_prod_ids)
    else:
        return False

def convert_memberships_and_magazines_to_included_products(obj, cr, uid, mem_mag_set):
    if isinstance(mem_mag_set, tuple):
        mem = [get_included_product_ids(obj,cr,uid,mem) for mem in mem_mag_set[0]] if mem_mag_set[0] else [get_included_product_ids(obj,cr,uid,False)]
        mag = [get_included_product_ids(obj,cr,uid,mag) for mag in mem_mag_set[1]] if mem_mag_set[1] else mem_mag_set[1]
        return (mem,[item for sublist in mag for item in sublist])
    else:
        return False

def join_memberships_with_magazines(mem_mag_set):
    if isinstance(mem_mag_set, tuple):
        return [sorted(set(mem_mag + mem_mag_set[1])) for mem_mag in mem_mag_set[0]]
    else:
        return False

class membership_membership_magazine(osv.osv):
    _name = 'membership.membership_magazine'

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Membership', select=True),
        'product_id': fields.many2one('product.product', 'Magazine', select=True),
        'date_to': fields.date('Datum tot'),
        'date_cancel': fields.date('Datum opgezegd'),
        'magazine_product': fields.boolean('Magazine'),
    }

membership_membership_magazine()

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


    def migrate_membership_magazine(self, cr, uid, ids, context=None):
        """
        temporary migrate code
        """
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.magazine_ids:
                raise osv.except_osv(_('Error'), _('Migratie is niet mogelijk'))
            else:
                prod_object = self.pool.get('product.product')
                if partner.membership_renewal_product_id:
                    gewoon_lid = get_included_product_ids(prod_object,cr,uid,False)
                    prod_ids = get_included_product_ids(prod_object,cr,uid,partner.membership_renewal_product_id.id)
                    if prod_ids != gewoon_lid:
                        magazine_obj = self.pool.get('membership.membership_magazine')
                        for product in prod_object.browse(cr, uid, prod_ids, context=context):
                            magazine_subscription_domain = [('partner_id','=',partner.id),('product_id','=',product.id)]
                            magazine_subscription_id = magazine_obj.search(cr,uid,magazine_subscription_domain)
                            vals = {
                               'partner_id':partner.id,
                               'product_id':product.id,
                               'date_to':'2017-12-31',
                               'magazine_product':product.magazine_product,
                            }
                            magazine_obj.create(cr, uid, vals, context=context)
        return True

    def recalc_membership(self, cr, uid, partner_id, context=None):
        partner = self.pool.get('res.partner').browse(cr, uid, [partner_id], context=context)[0]

        mline, membership_state_field = self._np_membership_state(cr, uid, partner, context=context)

#        membership_start_date = self._membership_start_date(cr, uid, [partner_id], None, None, context=context)
#        membership_start_date = membership_start_date[partner_id] if membership_start_date else None
#
#        membership_stop_date = self._membership_stop_date(cr, uid, [partner_id], None, None, context=context)
#        membership_stop_date = membership_stop_date[partner_id] if membership_stop_date else None
#
#        membership_cancel_date = self._membership_cancel_date(cr, uid, [partner_id], None, None, context=context)
#        membership_cancel_date = membership_cancel_date[partner_id] if membership_cancel_date else None
#
#        """ feature door axel niet nodig """
#        membership_renewal_date = None
#
#        membership_end_date = self._membership_end_date(cr, uid, [partner_id], None, None, context=context)
#        membership_end_date = membership_end_date[partner_id] if membership_end_date else None
#        

        membership_pay_date = None
        if membership_state_field == 'paid' and mline.account_invoice_line.invoice_id:
            ids = self.pool.get('account.invoice').search(cr, uid, [('id','=',mline.account_invoice_line.invoice_id.id)])
            for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
                for payment in invoice.payment_ids:
                    membership_pay_date = payment.date

        update_partner = False

#        if membership_state_field != partner.membership_state_b:
#            update_partner = True
#        if membership_start_date != partner.membership_start_b:
#            update_partner = True
#        if membership_stop_date != partner.membership_stop_b:
#            update_partner = True
        if membership_pay_date != partner.membership_pay_date:
            update_partner = True
#        if membership_end_date != partner.membership_end_b:
#            update_partner = True
#
        if update_partner:
            vals = {
                'membership_pay_date': membership_pay_date,
            }
            self.write(cr, uid, [partner.id], vals)
            cr.commit()
        return True

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
        data_inv = member_line_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            list_partner.append(data.partner.id)
        #ids2 = list_partner
        #while ids2:
        #    ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
        #    list_partner += ids2
        return list_partner

    def _get_invoice_partner(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        data_inv = inv_obj.browse(cr, uid, ids, context=context)
        list_partner = []
        for data in data_inv:
            if data.invoice_organisation:
                list_partner.append(data.membership_partner_id.id)
            else:
                list_partner.append(data.partner_id.id)
        #ids2 = list_partner
        #while ids2:
        #    ids2 = res_obj.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
        #    list_partner += ids2
        return list_partner

    def _get_magazine_partner(self, cr, uid, ids, context=None):
        magazines = self.pool.get('membership.membership_magazine').browse(cr, uid, ids, context=context)
        list_partner = [magazine.partner_id.id for magazine in magazines]
        return list(set(list_partner))

    def _np_membership_state(self, cr, uid, partner_data, date=None, context=None):
        if date == None:
            today = time.strftime('%Y-%m-%d')
        else:
            today = date

        if partner_data.free_member:
            return (None,'free')

        """ define the membership state rules """
        def membership_is_invoiced(mline,fstate):
            if fstate == 'open':
               if ( mline.account_invoice_line.invoice_id.sdd_mandate_id and mline.account_invoice_line.invoice_id.sdd_mandate_id.state == 'valid'
                  or mline.account_invoice_line.invoice_id.partner_id.abo_company
                  or mline.account_invoice_line.invoice_id.partner_id.company_deal
                  or mline.account_invoice_line.invoice_id.partner_id.organisation_type_id.id == 1
                  ):
                   return (mline,'invoiced')
            return False

        def membership_is_paid_or_does_not_need_to_be_paid(mline,fstate):
            if fstate == 'paid' or mline.account_invoice_line.invoice_id and mline.account_invoice_line.invoice_id.amount_total == 0.00:
                return (mline,'paid')
            else:
                return False

        def membership_via_website(mline,fstate):
            if fstate == 'open' and mline.account_invoice_line.invoice_id.website_payment:
                return (mline,'wait_member') if expired_membership_lines()[1] == 'old' else (mline,'none')
            else:
                return False

        membership_is_wait_member = lambda mline,fstate: (mline,'wait_member') if fstate == 'open' and not(mline.account_invoice_line.invoice_id.website_payment) else False
        membership_is_waiting = lambda mline,fstate: (mline,'waiting') if fstate == 'open' and mline.account_invoice_line.invoice_id.definitive_reject else False
        membership_is_canceled_or_refunded = lambda mline,fstate: (mline,'canceled') if fstate == 'cancel' else False
        """ end define membership state rules """

        def membership_fstate(mline):
            inv = mline.account_invoice_line.invoice_id
            if ((mline.membership_cancel_id or mline.date_cancel) and mline.date_to <= today
                or any([payment.invoice.type == 'out_refund' for payment in inv.payment_ids])
               ):
               return 'cancel'
            else:
                return inv.state

        def apply_state_rules_to_membership_lines(ids, rules):
            mstates = []
            migrated_fstate = lambda : 'cancel' if mline.membership_cancel_id or mline.date_cancel else 'paid'
            for mline in self.pool.get('membership.membership_line').browse(cr, SUPERUSER_ID, ids, context=context):
                if not(mline.membership_id and mline.membership_id.membership_product):
                    continue
                fstate = membership_fstate(mline) if mline.account_invoice_line.invoice_id else migrated_fstate()
                mstates.append([func(mline,fstate) for func in rules])
            mstates = recursive_flatten_list(mstates[0], mstates[1:], lambda x,y : x or y) if mstates else []
            """ return first non empty membership state """
            mstates = [s for s in mstates if s]
            return mstates[0] if mstates else (None,'none')

        def expired_membership_lines():
            domain = [('partner','=',partner_data.id),('date_from','<',today),('date_to','<',today)]
            ids = self.pool.get('membership.membership_line').search(cr, SUPERUSER_ID, domain)
            if ids:
                mline, mstate = apply_state_rules_to_membership_lines(ids,
                                                                      [membership_is_paid_or_does_not_need_to_be_paid,
                                                                       membership_is_canceled_or_refunded])
                return (mline,'old') if mstate == 'paid' else (mline,mstate)
            else:
                return (None,'none')

        """ loop the current membership lines """
        ids = self.pool.get('membership.membership_line').search(cr, SUPERUSER_ID, [('partner','=',partner_data.id),('date_to','>=',today)])
        if ids:
            """ hierarchy list of membership state conditions """
            mline, mstate = apply_state_rules_to_membership_lines(ids,
                                                                  [membership_is_paid_or_does_not_need_to_be_paid,
                                                                   membership_is_invoiced,
                                                                   membership_is_waiting,
                                                                   membership_via_website,
                                                                   membership_is_wait_member,
                                                                   membership_is_canceled_or_refunded])
            """ fallback to expired membership lines if there was no membership product ex. id 249991 """
            return (mline,mstate) if mline else expired_membership_lines()
        else:
            return expired_membership_lines()

    def _membership_state(self, cr, uid, ids, name, args, context=None):
        print 'CALC MEMBERSHIP STATE', name
        print 'ARGS:',args
        print 'CONTEXT:',context
#        if context:
#            if 'type' in context or not ('lang' in context):
#                return {}
## following line is to prevent update of standard membership_state field when creating a new invoice from the bank statement pop-up screen
#            if 'default_orig_name_save' in context:
#                return {}
#            if 'default_invoice_id' in context:
#                return{}
#            if 'skip_write' in context:
#                return {}
#            if 'mandate_id' in context:
#                return {}
#            if 'from_refund' in context:
#                return {}
#        else:
#            return {}
        """This Function return Membership State For Given Partner.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current userâID for security checks,
        @param ids: List of Partner IDs
        @param name: Field Name
        @param context: A standard dictionary for contextual values
        @param return: Dictionary of Membership state Value
        """
        res = {}
        print ids, name
        for id in ids:
            partner_data = self.browse(cr, SUPERUSER_ID, id, context=context)
            mline, membership_state = self._np_membership_state(cr, uid, partner_data, context=context)
            res[id] = membership_state
        return res

    def _membership_date(self, cr, uid, ids, name, args, context=None):
        print 'CALC MEMBERSHIP DATE:', ids
        """Return  date of membership"""
        if isinstance(name,list):
            name = name[0]
        res = {}
        member_line_obj = self.pool.get('membership.membership_line')
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.associate_member:
                partner_id = partner.associate_member.id
            else:
                partner_id = partner.id

            res[partner.id] = {
                 'membership_start': False,
                 'membership_stop': False,
                 'membership_end': False,
                 'membership_cancel': False
            }
            if name == 'membership_start':
                line_id = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('membership_id.membership_product', '=', True)],
                            limit=1, order='date_from', context=context)
                if line_id:
                    res[partner.id]['membership_start'] = member_line_obj.read(cr, uid, line_id[0], ['date_from'], context=context)['date_from']

            if name == 'membership_stop':
                line_id1 = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('membership_id.membership_product', '=', True)],
                            limit=1, order='date_to desc', context=context)
                if line_id1:
                    res[partner.id]['membership_stop'] = member_line_obj.read(cr, uid, line_id1[0], ['date_to'], context=context)['date_to']

            if name == 'membership_end':
                line_id3 = member_line_obj.search(cr, uid, [('partner', '=', partner_id),('membership_id.membership_product', '=', True),('state','=','paid')],
                            limit=1, order='date_to desc', context=context)
                if line_id3:
                    res[partner.id]['membership_end'] = member_line_obj.read(cr, uid, line_id3[0], ['date_to'], context=context)['date_to']

            if name == 'membership_cancel':
                mline, membership_state_field = self._np_membership_state(cr, uid, partner, context=context)
                if mline:
                    res[partner.id]['membership_cancel'] = datetime.today().strftime('%Y-%m-%d') if mline.date_cancel else False
        print "MEMBERSHIP STATE RES:",res
        return res

#    def _membership_start_date(self, cr, uid, ids, name, args, context=None):
#        if 1 == 1:
#            if name == 'membership_start':
#                return {}
#        """Return  date of membership"""
#        res = {}
#        member_line_obj = self.pool.get('membership.membership_line')
#        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
#            line_id = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True)],
#                            limit=1, order='date_from', context=context)
#            if line_id:
#                res[partner.id] = member_line_obj.read(cr, SUPERUSER_ID, line_id[0], ['date_from'], context=context)['date_from']
#        print "START DATE RES:",res
#        return res
#    def _membership_stop_date(self, cr, uid, ids, name, args, context=None):
#        if 1 == 1:
#            if name == 'membership_stop':
#                return {}
#        """Return  date of membership"""
#        res = {}
#        member_line_obj = self.pool.get('membership.membership_line')
#        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
#            line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True)],
#                            limit=1, order='date_to desc', context=context)
#            if line_id1:
#                res[partner.id] = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']
#        return res
#    def _membership_end_date(self, cr, uid, ids, name, args, context=None):
#        if 1 == 1:
#            if name == 'membership_end':
#                return {}
#        """Return  date of membership"""
#        res = {}
#        member_line_obj = self.pool.get('membership.membership_line')
#        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
#            line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True),('state','=','paid')],
#                            limit=1, order='date_to desc', context=context)
#            if line_id1:
#                res[partner.id] = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']
#        return res
#    def _membership_cancel_date(self, cr, uid, ids, name, args, context=None):
#        if 1 == 1:
#            if name == 'membership_cancel':
#                return {}
#        """Return  date of membership"""
#        res = {}
#        member_line_obj = self.pool.get('membership.membership_line')
#        for partner in self.browse(cr, SUPERUSER_ID, ids, context=context):
#            line_id1 = member_line_obj.search(cr, SUPERUSER_ID, [('partner', '=', partner.id),('membership_id.membership_product', '=', True),('state','=','canceled')],
#                            limit=1, order='date_cancel desc', context=context)
#            if line_id1:
#                cancel_date = member_line_obj.read(cr, SUPERUSER_ID, line_id1[0], ['date_to'], context=context)['date_to']
#                if partner.membership_end_f > cancel_date:
#                    res[partner.id] = None
#                else:
#                    res[partner.id] = cancel_date
#        return res

    def _get_partners(self, cr, uid, ids, context=None):
        ids2 = ids
        while ids2:
            ids2 = self.search(cr, uid, [('associate_member', 'in', ids2)], context=context)
            ids += ids2
        return ids

    def __get_membership_state(self, *args, **kwargs):
        return self._membership_state(*args, **kwargs)

    def _membership_renewal_product_id(self, cr, uid, ids, name, args, context=None):
        res = {}
        for id in ids:
            res[id] = self.get_membership_renewal_product(cr,uid,id,context=context)
        return res

    def get_membership_renewal_product(self, cr, uid, partner_id, context=None):
        """
        convert list of products to final renewal product id
        supports empty 'included_product_ids as default or a default
        membership product that includes itself (gewoon lid)
        @param partner_id: partner id
        @param return: product.product id
        """
        magazines = []
        prod_object = self.pool.get('product.product')
        default_renewal_product = get_included_product_ids(prod_object,cr,uid,False)
        partner = self.browse(cr, uid, [partner_id], context=context)[0]
        for magazine in partner.magazine_ids:
            if not magazine.date_cancel:
                magazines.append(magazine)
        magazine_ids = [m.product_id.id for m in magazines if m.date_to >= datetime.today().strftime('%Y-%m-%d')]
        if magazine_ids:
            renewal_products = sorted(default_renewal_product + magazine_ids)
            membership_product_ids = prod_object.search(cr, uid, [('membership_product','=',True)])
            for membership_product in prod_object.browse(cr, uid, membership_product_ids):
                if get_included_product_ids(prod_object,cr,uid,membership_product.id) == renewal_products:
                    return membership_product.id
        else:
            return default_renewal_product[0]

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
        #'membership_renewal_product_id': fields.many2one('product.product', 'Product Hernieuwing Lidmaatschap', select=True),
        'membership_renewal_product_id': fields.function(_membership_renewal_product_id,
                        string='Product Hernieuwing Lidmaatschap',
                        type='many2one',
                        relation='product.product',
                        store = {
                           'membership.membership_magazine': (_get_magazine_partner, ['date_cancel'], 12),
                        },
                        select=True),
		'free_membership_class_id': fields.many2one('res.partner.free.class', 'Gratis Lid Categorie', select=True),
        'magazine_ids': fields.one2many('membership.membership_magazine', 'partner_id', 'magazines', domain=[('magazine_product','=', True)]),
        'membership_state': fields.function(
                    _membership_state,
                    string = 'Current Membership Status', type = 'selection',
                    selection = STATE,
                    store = {
                        'account.invoice': (_get_invoice_partner, ['state'], 10),
                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
                        'res.partner': (_get_partners, ['free_member', 'associate_member'], 10)
                    }, help="""It indicates the membership state.
                    -Non Member: A partner who has not applied for any membership.
                    -Cancelled Member: A member who has cancelled his membership.
                    -Old Member: A member whose membership date has expired.
                    -Waiting Member: A member who has applied for the membership and whose invoice is going to be created.
                    -Invoiced Member: A member whose invoice has been created.
                    -Paying member: A member who has paid the membership fee."""),
        'membership_start': fields.function(
                    _membership_date, multi='membership_start',
                    string = 'Membership Start Date', type = 'date',
                    store = { 
                        'account.invoice': (_get_invoice_partner, ['state'], 10),
                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10, ),
                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10) 
                    }, help="Date from which the membership becomes active."),
        'membership_stop': fields.function(
                    _membership_date, multi='membership_stop',
                    string = 'Membership Stop Date', type = 'date',
                    store = { 
                        'account.invoice': (_get_invoice_partner, ['state'], 10),
                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10, ),
                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10) 
                    }, help="Date unitl which the membership remains active."),
        'membership_cancel': fields.function(
                    _membership_date, multi='membership_cancel',
                    string = 'Membership Cancel Date', type = 'date',
                    store = { 
                        'account.invoice': (_get_invoice_partner, ['state'], 10),
                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10, ),
                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10) 
                    }, help="Date on which the membership has been cancelled."),
        'membership_end': fields.function(
                    _membership_date, multi='membership_end',
                    string = 'Membership End Date', type = 'date',
                    store = { 
                        'account.invoice': (_get_invoice_partner, ['state'], 10),
                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10, ),
                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10) 
                    }, help="The last paid end date."),
#        'membership_start': fields.function(
#                    _membership_start_date, 
#                    string = 'Membership Start Date', type = 'date',
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10, ),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10)
#                    }, help="Date from which membership becomes active."),
#        'membership_stop': fields.function(
#                    _membership_stop_date,
#                    string = 'Membership End Date', type='date',
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10)
#                    }, help="Date until which membership remains active."),
#        'membership_cancel': fields.function(
#                    _membership_cancel_date,
#                    string = 'Cancel Membership Date', type='date',
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 11),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10)
#                    }, help="Date on which membership has been cancelled"),
#        'membership_end': fields.function(
#                    _membership_end_date, 
#                    string = 'Einddatum lidmaatschap', type='date',
#                    store = {
#                        'account.invoice': (_get_invoice_partner, ['state'], 10),
#                        'membership.membership_line': (_get_partner_id, ['state','date_from','date_to','date_cancel'], 10),
#                        'res.partner': (lambda self, cr, uid, ids, c={}: ids, ['free_member'], 10)
#                    }, help="Date until which membership remains active."),
        'free_member_comment': fields.char('Reden gratis lid'),
        'membership_renewal_date': fields.date('Lidmaatschap hernieuwingsdatum'),
        'membership_pay_date': fields.date('Lidmaatschap betaaldatum'),
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
                if member.account_invoice_id.sdd_mandate_id:
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

    def _np_membership_line_state(self, cr, uid, mline, context=None):

        """This Function returns current membership_renewal_product based on actual membership lines.
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user-id for security checks,
        @param mline: membership_line obj
        @param context: A standard dictionary for contextual values
        @param return: product.product id renewal product
        """

        prod_object = self.pool.get('product.product')

        """ start define rules """
        def membership_is_paid_or_does_not_need_to_be_paid(fstate):
            if fstate == 'paid' or mline.account_invoice_line.invoice_id and mline.account_invoice_line.invoice_id.amount_total == 0.00:
                inv = mline.account_invoice_line.invoice_id
                if inv and any([payment.invoice.type == 'out_refund' for payment in inv.payment_ids]):
                    return (mline.membership_id.id,'canceled') if mline.membership_id else False
                else:
                    return (mline.membership_id.id,'paid') if mline.membership_id else False
            else:
                return False

        def membership_is_invoiced(fstate):
            if fstate == 'open':
                membership_product = mline.membership_id
                return (membership_product.id,'invoiced') if membership_product else False
            else:
                return False

        def membership_is_canceled_or_refunded(fstate):
            inv = mline.account_invoice_line.invoice_id
            if fstate == 'cancel' or mline.membership_cancel_id or mline.date_cancel:
                membership_product = mline.membership_id
                return (membership_product.id,'canceled') if membership_product else False
            else:
                return False
        """ end define rules """

        def apply_renewal_rules_to_membership_line(mline, rules):
            mproducts = []
            migrated_fstate = lambda : 'cancel' if mline.membership_cancel_id or mline.date_cancel else 'paid'
            fstate = mline.account_invoice_line.invoice_id.state if not(mline.membership_cancel_id or mline.date_cancel) and mline.account_invoice_line.invoice_id else migrated_fstate()
            mproducts.append([func(fstate) for func in rules])
            flatten_func = lambda set1,set2 : set1 + set2 if all([set1,set2]) else set1 if set1 else set2
            state_prod_list = recursive_flatten_list(mproducts[0], mproducts[1:], flatten_func) if mproducts else []
            state_prod_list = [state_prod for state_prod in state_prod_list if state_prod]
            return state_prod_list[0] if state_prod_list else (False,False)

        def products_to_renew_from_membership_line():
            """loop througt membership lines and return
            list of products that should be renewed with next invoice
            We can only renew 1 product so the return value still needs to be
            converted to a membership product that includes all to renew products
            @param return: list of products to renew or False
            """
            # process membership lines
            membership_magazines,state = apply_renewal_rules_to_membership_line(mline,
                                             [membership_is_paid_or_does_not_need_to_be_paid,
                                              membership_is_invoiced,
                                              membership_is_canceled_or_refunded])
            return state,compose(partial(split_memberships_and_magazines,prod_object,cr,uid),
                                 partial(convert_memberships_and_magazines_to_included_products,prod_object,cr,uid),
                                 join_memberships_with_magazines)(membership_magazines)
        state, product_ids = products_to_renew_from_membership_line()
        return state, product_ids[0] if product_ids else False

    def set_magazine_subscriptions(self, cr, uid, partner_id, product_ids, state, context=None):
        """create/update magazine subscriptions
        @param return: date of longest running magazine subscription
        """
        magazine_obj = self.pool.get('membership.membership_magazine')
        prod_object = self.pool.get('product.product')
        gewoon_lid = get_included_product_ids(prod_object,cr,uid,False)
        res = []
        for product in prod_object.browse(cr, uid, product_ids, context=context):
             magazine_subscription_domain = [('partner_id','=',partner_id),('product_id','=',product.id)]
             magazine_subscription_id = magazine_obj.search(cr,uid,magazine_subscription_domain)
             if product.magazine_product and state == 'paid' or not product.magazine_product:
                 if magazine_subscription_id:
                    vals = {
                       'date_to':product.membership_date_to,
                       'date_cancel':False,
                       'magazine_product':product.magazine_product,
                    }
                    magazine_obj.write(cr, uid, magazine_subscription_id, vals, context=context)
                    if product.id not in gewoon_lid:
                        res.append(product.membership_date_to)
                 else:
                    vals = {
                       'partner_id':partner_id,
                       'product_id':product.id,
                       'date_to':product.membership_date_to,
                       'magazine_product':product.magazine_product,
                    }
                 magazine_obj.create(cr, uid, vals, context=context)
                 if product.id not in gewoon_lid:
                     res.append(product.membership_date_to)
        # return higest membership_date_to of magazine subscriptions
        return max(res) if res else False

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
        for mline in self.browse(cr, SUPERUSER_ID, ids, context=context):
            state, product_ids  = self._np_membership_line_state(cr, SUPERUSER_ID, mline, context=context)
            res[mline.id] = state
            if product_ids:
                membership_date_to = self.set_magazine_subscriptions(cr, uid, mline.partner.id, product_ids, state, context=context)
                if state == 'paid':
                    payments = mline.account_invoice_line.invoice_id.payment_ids
                    assert len(payments) == 1, "only 1 payment is accepted"
                    for payment in payments:
                        # new member
                        if mline.partner.membership_end == False:
                            vals = {
                                'date_from': payment.date,
                                'date_to': membership_date_to,
                            }
                        else:
                            year = datetime.now().year
                            d = lambda y,m,d : datetime(y,m,d).strftime('%Y-%m-%d')
                            cutoff_date = d(year,9,1)
                            date_from = d(year,1,1) if payment.date < cutoff_date else cutoff_date
                            offset = 0 if payment.date < cutoff_date else 1
                            date_to = d(year+offset,12,31)
                            vals = {
                                'date_from': date_from,
                                'date_to': date_to,
                            }
                        self.write(cr, uid, ids, vals, context=context)
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
                        'res.partner': (_get_partners, ['membership_state'], 12),
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
