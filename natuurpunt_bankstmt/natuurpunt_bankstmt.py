# -*- encoding: utf-8 -*-

import datetime
from mx import DateTime
import time

from osv import fields, osv
from openerp import netsvc
from openerp.tools.translate import _

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

def get_country_city_from_zip_code(obj,cr,uid,zip_code):
    country_city_obj = obj.pool.get('res.country.city')
    ids = country_city_obj.search(cr, uid, [('zip','=',zip_code)])
    if ids: 
        return country_city_obj.browse(cr, uid, ids[0])
    else:
        return False

def get_street(obj,cr,uid,city_id,street):
    country_city_street_obj = obj.pool.get('res.country.city.street')
    ids = country_city_street_obj.search(cr, uid, [('city_id','=',city_id),('name','=',street)])
    if ids:
        return country_city_street_obj.browse(cr, uid, ids[0])
    else:
        return False

class account_bank_statement_line(osv.osv):
    _inherit = "account.bank.statement.line"

    def onchange_type(self, cr, uid, line_id, partner_id, type, context=None):
        res = {'value': {}}
        obj_partner = self.pool.get('res.partner')
        if context is None:
            context = {}
        if not partner_id:
            return res
        account_id = False

        line = self.browse(cr, uid, line_id, context=context)
        part = obj_partner.browse(cr, uid, partner_id, context=context)
        if type == 'supplier':
            account_id = part.property_account_payable.id
        else:
            if type == 'customer':
                account_id = part.property_account_receivable.id
            else:
                tmp_accounts = self.pool.get('account.account').search(cr, uid, [('code', '=', '499010')])
                if tmp_accounts and len(tmp_accounts) > 0:
                    account_id = tmp_accounts[0]
                
        res['value']['account_id'] = account_id
        return res

#    def dtl_lines(self, cr, uid, ids, context=None):
#        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','account.coda.det2'),
#                                                            ('name','=','view.bank.statement.det.tree')])
#        stmt = self.browse(cr, uid, ids)[0]
#        if stmt.id and stmt.det2_ids:
#            context['default_stat_line_id'] = stmt.id
#        else:
#            return
#
#        return {
#            'type': 'ir.actions.act_window',
#            'name': 'Detail Coda',
#            'view_mode': 'form',
#            'view_type': 'form',
#            'view_id': view_id[0],
#            'res_model': 'account.coda.det2',
#            'target': 'new',
#            'context': context,
#        }

    def create_partner(self, cr, uid, ids, context=None):
        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','bank.statement.create.partner'),
                                                            ('name','=','view.bank.statement.create.partner.form')])
        stmt = self.browse(cr, uid, ids)[0]
        if stmt.lines2_id and stmt.lines2_id.t23_partner:
            context['stmt_id'] = stmt.id
            context['default_stmt_id'] = stmt.id
            context['default_transaction_amount'] = stmt.amount
            context['default_coda_amount'] = stmt.lines2_id.t21_amount
            context['default_free_comm'] = stmt.lines2_id.t21_free_comm
            context['default_orig_name'] = stmt.lines2_id.t23_partner
            context['default_orig_name_save'] = stmt.lines2_id.t23_partner
            context['default_partner_id'] = stmt.partner_id.id

            account_coda_koalect_obj = self.pool.get('account.coda.koalect')
            koalect_ids = account_coda_koalect_obj.search(cr, uid, [('stat_line_id','=',stmt.id)])
            if koalect_ids:
                koalect = account_coda_koalect_obj.browse(cr, uid, koalect_ids)[0]
                context['default_add_bank_account'] = False
                context['default_name_coda'] = koalect.firstname + ' ' + koalect.lastname
                context['default_last_name'] = koalect.lastname
                context['default_first_name'] = koalect.firstname
                country_city = get_country_city_from_zip_code(self,cr,uid,koalect.postal_code)
                if country_city:
                    context['default_zip_id'] = country_city.id
                    context['default_zip'] = country_city.zip
                    context['default_city'] = country_city.name
                    country_city_street = get_street(self,cr,uid,country_city.id,koalect.street)
                    if country_city_street:
                        context['default_street_id']  = country_city_street.id
                        context['default_street']     = country_city_street.name
                else:
                    context['default_zip_id'] = 0
                    context['default_zip'] = koalect.postal_code
                    context['default_city'] = koalect.city
                    context['default_street_id'] = 0
                    context['default_street'] = koalect.street
                context['default_street_nbr'] = koalect.number
            else:
                #context['default_add_bank_account'] = True
                context['default_bic'] = stmt.lines2_id.t22_BIC
                context['default_bank_account'] = stmt.lines2_id.t23_account_nbr
                name = stmt.lines2_id.t23_partner
                nbr_words_name = len(name.split())
                if nbr_words_name > 1:
                    first_name = name.split()[nbr_words_name - 1]
                    last_name = name.replace((' ' + first_name),'')
                    first_name_lu = first_name[0:1] + first_name[1:].lower()
                    last_name_lu = last_name[0:1] + last_name[1:].lower()
                    context['default_name_coda'] = first_name_lu + ' ' + last_name_lu
                    context['default_last_name'] = last_name_lu
                    context['default_first_name'] = first_name_lu
                else:
                    context['default_name_coda'] = stmt.lines2_id.t23_partner
                    context['default_last_name'] = stmt.lines2_id.t23_partner
                lines3_obj = self.pool.get('account.coda.lines3')
                lines3 = lines3_obj.search(cr, uid, [('lines2_id','=',stmt.lines2_id.id)])
                if lines3:
                    lines3_id = lines3_obj.browse(cr, uid, lines3[0])
                    if lines3_id.t32_free_comm:
                        context['default_orig_address'] = lines3_id.t32_free_comm
                        country_city = get_country_city_from_zip_code(self,cr,uid,lines3_id.t32_free_comm[35:39])
                        if country_city:
                            context['default_zip_id'] = country_city.id
                            context['default_zip'] = country_city.zip
                            context['default_city'] = country_city.name
                            street_orig = lines3_id.t32_free_comm[0:35].rstrip()
                            wrdcount = 0
                            for i in street_orig.split():
                                eawrdlen = len(i) / len(i)
                                wrdcount = wrdcount + eawrdlen
                            street = ''
                            street_lu = ''
                            if wrdcount < 3:
                                street = street_orig.split()[0]
                                street_lu = street[0:1] + street[1:].lower()
                            else:
                                for i in range(1, wrdcount):
                                    if street =='':
                                        street = street_orig.split()[(i - 1)]
                                        street_lu = street[0:1] + street[1:].lower()
                                    else:
                                        street = street + ' ' + street_orig.split()[(i - 1)]
                                        street_lu = street_lu + ' ' + street_orig.split()[(i - 1)][0:1] + street_orig.split()[(i - 1)][1:].lower()
                            country_city_street = get_street(self,cr,uid,country_city.id,street_lu)
                            if country_city_street:
                                context['default_street_id']  = country_city_street.id
                                context['default_street']     = country_city_street.name
                                context['default_street_nbr'] = street_orig.replace((street + ' '),'')
                            else:
                                context['default_street'] = lines3_id.t32_free_comm[0:35].rstrip()

                        else:
                            context['default_city'] = lines3_id.t32_free_comm[35:80].rstrip()
                            context['default_street'] = lines3_id.t32_free_comm[0:35].rstrip()

            if stmt.partner_id:
                context['default_partner_address'] = stmt.partner_id.street + ' ' + stmt.partner_id.zip + ' ' + stmt.partner_id.city
                context['default_membership_nbr'] = stmt.partner_id.membership_nbr
                if stmt.partner_id.membership_state == 'none':
                    membership_state = 'Geen lid'
                else:
                    if stmt.partner_id.membership_state == 'canceled':
                        membership_state = 'Opgezegd lid'
                    else:
                        if stmt.partner_id.membership_state == 'old':
                            membership_state = 'Oud lid'
                        else:
                            if stmt.partner_id.membership_state == 'waiting':
                                membership_state = 'Wachtend lid'
                            else:
                                if stmt.partner_id.membership_state == 'invoiced':
                                    membership_state = 'Gefactureerd lid'
                                else:
                                    if stmt.partner_id.membership_state == 'paid':
                                        membership_state = 'Betaald lid'
                                    else:
                                        if stmt.partner_id.membership_state == 'wait_member':
                                            membership_state = 'Wachtend lidmaatschap'
                                        else:
                                            if stmt.partner_id.membership_state == 'free':
                                                membership_state = 'Gratis lid'
                                            else:
                                                membership_state = 'Geen lid'
                context['default_membership_state'] = membership_state

        return {
            'type': 'ir.actions.act_window',
            'name': 'Aanmaken Partner',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': view_id[0],
            'res_model': 'bank.statement.create.partner',
            'target': 'new',
            'context': context,
            }

    def write(self, cr, uid, ids, vals, context=None):
        if 'partner_id' in vals and (not(vals['partner_id']) or vals['partner_id'] == ''):
            for absl in ids:
                sql_stat = 'update account_bank_statement_line set partner_id = NULL where id = %d' % (absl, )
                cr.execute(sql_stat)
                cr.commit()
                del vals['partner_id']
        if 'partner_id2' in vals and vals['partner_id2']:
            for absl in ids:
                sql_stat = 'update account_bank_statement_line set partner_id = %d where id = %d' % (vals['partner_id2'], absl, )
                cr.execute(sql_stat)
                cr.commit()
        return super(account_bank_statement_line, self).write(cr, uid, ids, vals, context)

    _columns = {
        }

account_bank_statement_line()

class bank_statement_create_partner(osv.osv_memory):
    _name = "bank.statement.create.partner"

    def onchange_name(self, cr, uid, ids, first_name, last_name, orig_name, context=None):
        res = {}
        res['name_coda'] = orig_name
        if not first_name:
            if last_name == '':
                return
            else:
                res['name_coda'] = last_name
        else:
            if not last_name:
                res['name_coda'] = first_name
            else:
                res['name_coda'] = first_name + ' ' + last_name
        if not (first_name or last_name):
            res['name_coda'] = orig_name
            
        return {'value':res}

    def onchange_donation_partner(self, cr, uid, ids, donation_partner, donation_product_id, context=None):
        res={}
        if donation_partner and not donation_product_id:
            prod_obj = self.pool.get('product.product')
            prod_ids = prod_obj.search(cr, uid, [('donation_product_bank_stmt','=',True)])
            if len(prod_ids) == 1:
                prod = prod_obj.browse(cr, uid, prod_ids[0])
                res['donation_product_id'] = prod.id
        if not donation_partner:
            res['donation_amount'] = 0
            res['donation_amount_inv'] = 0
            res['donation_partner'] = False
            res['donation_product_id'] = False
        return {'value':res}                
    
    def onchange_product_id(self, cr, uid, ids, product_id, transaction_amount, donation_partner, membership_partner, donation_product_id, context=None):
        res = {}
        membership_amount = 0.00
        donation = donation_partner
        if product_id and membership_partner:
            product_obj = self.pool.get('product.product')
            product = product_obj.browse(cr, uid, product_id, context=context)
            membership_amount = product.list_price
        if membership_partner:
            res['membership_amount'] = membership_amount
            res['membership_amount_inv'] = membership_amount
        donation_amount = transaction_amount - membership_amount
        if donation_amount > 0.00:
            res['donation_amount'] = donation_amount
            res['donation_amount_inv'] = donation_amount
            res['donation_partner'] = True
            donation = True
        else:
            res['donation_amount'] = 0
            res['donation_amount_inv'] = 0
            res['donation_partner'] = False
            res['donation_product_id'] = False
            donation = False
        if donation_amount < 0.00:
            return {'warning': { 
                                'title': _('Warning!'),
                                'message': _('Bedrag lidmaatschap groter dan betaald bedrag')}}
            
#         else:
# # warning toevoegen - transaction_amount < membership_amount
#             warning = {}
#             title = False
#             message = False
# 
#             if result.get('warning',False):
#                 warning['title'] = title and title +' & '+ result['warning']['title'] or result['warning']['title']
#                 warning['message'] = message and message + ' ' + result['warning']['message'] or result['warning']['message']
#     
#                 return {'value': result.get('value',{}), 'warning':warning}
#                         
#                         
#                         
#                         
#                         res['donation_partner'] = False
#                         donation = False
#                         raise osv.except_osv(('Waring'),_('Bedrag lidmaatschap groter dan betaald bedrag'))
#                         return {'warning': { 
#                                             'title': _('Warning!'),
#                                             'message': _('Bedrag lidmaatschap groter dan betaald bedrag')}}
        if donation and not donation_product_id:
            prod_obj = self.pool.get('product.product')
            prod_ids = prod_obj.search(cr, uid, [('donation_product_bank_stmt','=',True)])
            if len(prod_ids) == 1:
                prod = prod_obj.browse(cr, uid, prod_ids[0])
                res['donation_product_id'] = prod.id

        return {'value':res}

    def onchange_membership_amount(self, cr, uid, ids, transaction_amount, membership_amount, donation_product_id, context=None):
        res = {}
        donation_amount = 0.00
        donation_amount = transaction_amount - membership_amount
        res['membership_amount_inv'] = membership_amount
        if donation_amount > 0.00:
            res['donation_amount'] = donation_amount
            res['donation_amount_inv'] = donation_amount
            res['donation_partner'] = True
            donation = True
        else:
            res['donation_amount'] = 0
            res['donation_amount_inv'] = 0
            res['donation_partner'] = False
            res['donation_product_id'] = False
            donation = False
        if donation_amount < 0.00:
            return {'warning': { 
                                'title': _('Warning!'),
                                'message': _('Bedrag lidmaatschap groter dan betaald bedrag')}}
        if donation and not donation_product_id:
            prod_obj = self.pool.get('product.product')
            prod_ids = prod_obj.search(cr, uid, [('donation_product_bank_stmt','=',True)])
            if len(prod_ids) == 1:
                prod = prod_obj.browse(cr, uid, prod_ids[0])
                res['donation_product_id'] = prod.id
        
        return {'value':res}

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

#     def _openinvoicelines_ids(self, cr, uid, ids, name, args, context=None):
#                 result = {}
#                 print 'open invoices zoeken'
#                 for statementpartner in self.browse(cr, uid, ids, context=context):
#                         result[statementpartner.id] = {}
#                         openinvoices = []
#                         print partner.invoice_ids
#                         for invoicelines in statementpartner.partner_id.invoice_ids:
#                                 print 'invoice', invoicelines
#                                 if invoicelines.invoice_id.state == 'open':
#                                         openinvoices += invoicelines.id
#                         result[statementpartner.id]['open_invoicelines_ids'] = openinvoices
# 
#                 return result

    _columns = {
        'name_coda': fields.char('Naam'),
        'last_name': fields.char('Familienaam'),
        'first_name': fields.char('Voornaam'),
        'street': fields.char('Straat'),
        'zip': fields.char('Postcode', size=16),
        'city': fields.char('Gemeente'),
                'zip_id': fields.many2one('res.country.city', 'Gemeente'),
                'street_id': fields.many2one('res.country.city.street', 'Straat'),
                'street_nbr': fields.char('Nummer', size=16),
                'street_bus': fields.char('Bus', size=16),
                'orig_name': fields.char('Coda Naam'),
                'orig_name_save': fields.char('Coda Naam'),
                'orig_address': fields.char('Coda Adres'),
                'membership_partner': fields.boolean('Lidmaatschap'),
                'membership_product_id': fields.many2one('product.product', 'Product Lidmaatschap', select=True),
                'bic': fields.char('BIC Code', size=16),
                'bank_account': fields.char('Bankrekening', size=20),
                'coda_amount': fields.float('Coda bedrag'),
                'transaction_amount': fields.float('Bedrag transactie'),
                'membership_origin_id': fields.many2one('res.partner.membership.origin', 'Herkomst Lidmaatschap', select=True),
                'free_comm': fields.char('Vrije Communicatie'),
                'partner_id': fields.many2one('res.partner', 'Partner', select=True),
                'add_bank_account': fields.boolean('Bankrekening Toevoegen'),
                'membership_nbr': fields.char('Lidnummer'),
                'membership_state': fields.char('Status Lidmaatschap', translate=True),
                'partner_address': fields.char('Adres'),
                'accept_address': fields.boolean('Adres Aanvaarden'),
                'double_address_id': fields.integer('ID adrescontrole'),
                'double_address': fields.text('Adrescontrole'),
        'membership_product_amount': fields.related('membership_product_id', 'list_price', type='amount', string="List price"),
                'stmt_id': fields.many2one('account.bank.statement.line', 'Lijn Rekeninguitreksel', select=True),
        'donation_partner': fields.boolean('Gift'),
                'analytic_account_id': fields.many2one('account.analytic.account', 'Analytische Rekening', select=True),
        'donation_amount': fields.float('Bedrag Gift'),
        'donation_amount_inv': fields.float('Bedrag Gift'),
        'membership_amount': fields.float('Bedrag Lidmaatschap'),
        'membership_amount_inv': fields.float('Bedrag Lidmaatschap'),
                'donation_product_id': fields.many2one('product.product', 'Product Gift', select=True),
                'gender': fields.selection([('M','Man'),('V','Vrouw'),('O','Ongekend')], string='Geslacht', size=1),
                'openinvoice_id': fields.integer('Open lidmaatschapfactuur'),
                'openinvoice_nbr': fields.text('Bestaande open factuur'),
                'openinvoice_amount': fields.float('Bedrag factuur'),
                'openinvoice_del': fields.boolean('Factuur verwijderen')
#                 'open_invoicelines_id': 
#                                 fields.function(
#                                         _openinvoicelines_ids,
#                                         string='Faktuurregels',
#                                         type='many2many',
#                                         relation='account.invoice.line'),
    }

    _defaults = {
                'add_bank_account':True,
    }

    def onchange_zip_id(self, cr, uid, ids, zip_id, context=None):
        res = {}
        if not zip_id:
            res['city'] = ""
            res['zip'] = ""
        else:
            city_obj = self.pool.get('res.country.city')
            city = city_obj.browse(cr, uid, zip_id, context=context)
            res['city'] = city.name
            res['zip'] = city.zip
 
        return {'value':res}

    def onchange_street_id(self, cr, uid, ids, street_id, street_nbr, street_bus, context=None):
        res = {}
        if not street_id:
            res['street'] = ""
        else:
            street_obj = self.pool.get('res.country.city.street')
            street = street_obj.browse(cr, uid, street_id, context=context)
            res['street'] = street.name

        error_msg = ''
        double_address_id = False
        if street_id and street_nbr:
            address_obj = self.pool.get('res.partner')
            if street_bus:
                   address_search = address_obj.search(cr, uid, [('street_id','=',street_id),('street_nbr','=',street_nbr),('street_bus','=',street_bus)])
            else:
                   address_search = address_obj.search(cr, uid, [('street_id','=',street_id),('street_nbr','=',street_nbr)])
            if address_search:
                for address_get in address_obj.browse(cr, uid, address_search):
                    if double_address_id == False:
                        double_address_id = address_get.id
                    error_msg = error_msg + address_get.name + ' (' + str(address_get.id) + ')'
                    error_msg = error_msg + '''
'''
        res['double_address'] = error_msg
        res['double_address_id'] = double_address_id

        return {'value':res}

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = {}
        if partner_id:
            partner_obj = self.pool.get('res.partner')
            partner = partner_obj.browse(cr, uid, partner_id, context=context)
            if partner.membership_state == 'none':
                    membership_state = 'Geen lid'
            else:
                    if partner.membership_state == 'canceled':
                            membership_state = 'Opgezegd lid'
                    else:
                            if partner.membership_state == 'old':
                                    membership_state = 'Oud lid'
                            else:
                                    if partner.membership_state == 'waiting':
                                            membership_state = 'Wachtend lid'
                                    else:
                                            if partner.membership_state == 'invoiced':
                                                    membership_state = 'Gefactureerd lid'
                                            else:
                                                    if partner.membership_state == 'paid':
                                                            membership_state = 'Betaald lid'
                                                    else:
                                                            if partner.membership_state == 'wait_member':
                                                                    membership_state = 'Wachtend lidmaatschap'
                                                            else:
                                                                    if partner.membership_state == 'free':
                                                                            membership_state = 'Gratis lid'
                                                                    else:
                                                                            membership_state = 'Geen lid'
            res['membership_nbr'] = partner.membership_nbr
            res['membership_state'] = membership_state
            res['partner_address'] = partner.street + ' ' + partner.zip + ' ' + partner.city
    

            for invoicelines in partner.invoice_ids:
                    if invoicelines.invoice_id.state == 'open' and invoicelines.invoice_id.membership_invoice:
                            res['openinvoice_id']=invoicelines.invoice_id.id
                            res['openinvoice_nbr']=invoicelines.invoice_id.number
                            res['openinvoice_amount']=invoicelines.invoice_id.amount_total
                        
        return {'value':res}

    def create_partner(self, cr, uid, ids, context=None):
        res = {}
        partner_obj = self.pool.get('res.partner')
        for partner in self.browse(cr, uid, ids, context):
            partner_name = ''
            if partner.last_name:
                partner_name = partner.last_name
            if partner.first_name:
                partner_name = partner.first_name + ' ' + partner_name
            if partner.street_nbr:
                if partner.street_bus:
                    street = partner.street + ' ' + partner.street_nbr + '/' + partner.street_bus
                else:
                    street = partner.street + ' ' + partner.street_nbr
            else:
                street = partner.street
            if partner.membership_origin_id:
                membership_origin_id = partner.membership_origin_id.id
            else:
                membership_origin_id = None
            if partner.partner_id:
                partner_id = partner.partner_id.id
                if membership_origin_id:
                    partner_obj.write(cr, uid, partner_id,{
                        'membership_origin_id': membership_origin_id,
                    }, context=context)
            else:
                if partner.accept_address:
                    partner_id = partner.double_address_id
                else:
                    partner_id = partner_obj.create(cr, uid, {
                     'name': partner_name,
                     'last_name': partner.last_name,
                     'first_name': partner.first_name,
                     'gender': partner.gender,
                     'street': street,
                     'zip': partner.zip,
                     'city': partner.city,
                     'zip_id': partner.zip_id.id,
                     'street_id': partner.street_id.id,
                     'street_nbr': partner.street_nbr,
                     'street_bus': partner.street_bus,
                     'country_id': 21,
                     'membership_origin_id': membership_origin_id,
                     'lang': 'nl_BE',
                     'membership_state': 'none',
                     'membership_nbr': None,
                     'crab_used': True,
                     'bank_ids': False,
                     'customer': False,
                     'supplier': False,
                    }, context)
            res['partner_id'] = partner_id

            if partner.add_bank_account:
                bank_obj = self.pool.get('res.bank')
                bank = bank_obj.search(cr, uid, [('bic','=',partner.bic)])
                if bank:
                    bank_rec = bank_obj.browse(cr, uid, bank[0])
                    bank_id = bank_rec.id
                else:
                    bank_id = bank_obj.create(cr, uid, {
                        'name': partner.bic,
                        'bic': partner.bic,
                        'active': True,
                    }, context=context)

                street = '' 
                if partner.street:
                    street = partner.street
                if partner.street_nbr:
                    street = street + ' ' + partner.street_nbr
                partner_bank_obj = self.pool.get('res.partner.bank')
                partner_bank_id = partner_bank_obj.create(cr, uid, {
                    'bank_name': partner.bic,
                    'owner_name': partner.name_coda,
                    'sequence': 50,
                    'street': street,
                    'partner_id': partner_id,
                    'bank': bank_id,
                    'bank_bic': partner.bic,
                    'city': partner.city,
                    'name': partner_name,
                    'zip': partner.zip,
                    'country_id': 21,
                    'state': 'iban',
                    'acc_number': partner.bank_account,
                }, context=context) 
            else:
                print 'BANK ACCOUNT NIET TOEGEVOEGD'

        if 'stmt_id' in context and context['stmt_id']:
            stmt_obj = self.pool.get('account.bank.statement.line')
            stmt = stmt_obj.search(cr, uid, [('id','=',context['stmt_id'])])
            stmt_obj.write(cr, uid, stmt, {
                'partner_id2': partner_id,
            }, context=context)
            
        return {'type':'ir.actions.act_window_close'}

    def create_partner_invoice(self, cr, uid, ids, context=None):
        res = {}
        partner_obj = self.pool.get('res.partner')
        create_membership = False
        create_donation = False

        for partner in self.browse(cr, uid, ids, context):
            partner_name = ''
            if partner.last_name:
                partner_name = partner.last_name
            if partner.first_name:
                partner_name = partner.first_name + ' ' + partner_name
            if partner.street_nbr:
                if partner.street_bus:
                    street = partner.street + ' ' + partner.street_nbr + '/' + partner.street_bus
                else:
                    street = partner.street + ' ' + partner.street_nbr
            else:
                street = partner.street
            if partner.membership_origin_id:
                membership_origin_id = partner.membership_origin_id.id
            else:
                membership_origin_id = None
            if partner.partner_id:
                partner_id = partner.partner_id.id
                if membership_origin_id:
                    partner_obj.write(cr, uid, partner_id,{
                        'membership_origin_id': membership_origin_id,
                    }, context=context)
            else:
                   partner_id = partner_obj.create(cr, uid, {
                    'name': partner_name,
                    'last_name': partner.last_name,
                    'first_name': partner.first_name,
                    'gender': partner.gender,
                    'street': street,
                    'zip': partner.zip,
                    'city': partner.city,
                    'zip_id': partner.zip_id.id,
                    'street_id': partner.street_id.id,
                    'street_nbr': partner.street_nbr,
                    'street_bus': partner.street_bus,
                    'country_id': 21,
                    'out_inv_comm_type': 'bba',
                    'out_inv_comm_algorithm': 'partner_ref',
                    'membership_origin_id': membership_origin_id,
                    'lang': 'nl_BE',
                    'membership_state': 'none',
                    'membership_nbr': None,
                    'crab_used': True,
                    'bank_ids': False,
                    'customer': False,
                    'supplier': False,
                    }, context=context)
            res['partner_id'] = partner_id

            print 'ADD BANK ACCOUNT:',partner.add_bank_account
            if partner.add_bank_account:
                print 'BANK ACCOUNT TOEGEVOEGD'
                bank_obj = self.pool.get('res.bank')
                bank = bank_obj.search(cr, uid, [('bic','=',partner.bic)])
                if bank:
                    bank_rec = bank_obj.browse(cr, uid, bank[0])
                    bank_id = bank_rec.id
                else:
                    bank_id = bank_obj.create(cr, uid, {
                        'name': partner.bic,
                        'bic': partner.bic,
                        'active': True,
                    }, context=context)

                street = '' 
                if partner.street:
                    street = partner.street
                if partner.street_nbr:
                    street = street + ' ' + partner.street_nbr
                if not partner.partner_id:            
                    partner_bank_obj = self.pool.get('res.partner.bank')
                    partner_bank_id = partner_bank_obj.create(cr, uid, {
                        'bank_name': partner.bic,
                        'owner_name': partner.name_coda,
                        'sequence': 50,
                        'street': street,
                        'partner_id': partner_id,
                        'bank': bank_id,
                        'bank_bic': partner.bic,
                        'city': partner.city,
                        'name': partner_name,
                        'zip': partner.zip,
                        'country_id': 21,
                        'state': 'iban',
                        'acc_number': partner.bank_account,
                    }, context=context)

            cr.commit()

            if partner.membership_partner:
                create_membership = True

                invoice_obj = self.pool.get('account.invoice')
                invoice_line_obj = self.pool.get('account.invoice.line')
                invoice_tax_obj = self.pool.get('account.invoice.tax')

                partner_rec = partner_obj.browse(cr, uid, partner_id)

                product_id = partner.membership_product_id.id
                analytic_dimension_1_id = partner.membership_product_id.analytic_dimension_1_id.id
                analytic_dimension_2_id = partner.membership_product_id.analytic_dimension_2_id.id
                analytic_dimension_3_id = partner.membership_product_id.analytic_dimension_3_id.id

#                amount_inv = partner.membership_product_id.product_tmpl_id.list_price
                amount_inv = partner.membership_amount_inv

                account_id = partner_rec.property_account_receivable and partner_rec.property_account_receivable.id or False
                fpos_id = partner_rec.property_account_position and partner_rec.property_account_position.id or False

                quantity = 1

                payment_term_id = None
                mandate_id = None
            
                line_value = {}
                line_dict = invoice_line_obj.product_id_change(cr, uid, {}, product_id, False, quantity, '', 'out_invoice', partner_id, fpos_id, price_unit=amount_inv, context=context)
                line_value.update(line_dict['value'])
                line_value['price_unit'] = amount_inv
                if line_value.get('invoice_line_tax_id', False):
                    tax_tab = [(6, 0, line_value['invoice_line_tax_id'])]
                    line_value['invoice_line_tax_id'] = tax_tab
                line_value['analytic_dimension_1_id'] = analytic_dimension_1_id
                line_value['analytic_dimension_2_id'] = analytic_dimension_2_id
                line_value['analytic_dimension_3_id'] = analytic_dimension_3_id
                line_value['product_id'] = product_id

                today = datetime.date.today()
                days30 = datetime.timedelta(days=30)
                datedue = today + days30

                reference = invoice_obj.generate_bbacomm(cr, uid, ids, 'out_invoice', 'bba', partner_id, '', context={})
                referenc2 = reference['value']['reference']

                invoice_id = invoice_obj.create(cr, uid, {
                    'partner_id': partner_id,
                    'membership_partner_id': partner_id,
                    'account_id': account_id,
                    'membership_invoice': True,
                    'third_payer_id': None,
                    'third_payer_amount': 0.00,
                    'fiscal_position': fpos_id or False,
                    'payment_term': 3,
                    'sdd_mandate_id': None,
                    'reference_type': 'bba',
                    'type': 'out_invoice',
                    'reference': referenc2,
                    'date_due': datedue,
                    'internal_number': None,
                    'number': None,
                    'move_name': None,
                }, context=context)

                line_value['invoice_id'] = invoice_id
                invoice_line_id = invoice_line_obj.create(cr, uid, line_value, context=context)
                invoice_obj.write(cr, uid, invoice_id, {'invoice_line': [(6, 0, [invoice_line_id])]}, context=context)
                if 'invoice_line_tax_id' in line_value and line_value['invoice_line_tax_id']:
                    tax_value = invoice_tax_obj.compute(cr, uid, invoice_id).values()
                    for tax in tax_value:
                        invoice_tax_obj.create(cr, uid, tax, context=context)

                    wf_service = netsvc.LocalService('workflow')
                    wf_service.trg_validate(uid, 'account.invoice', invoice_id, 'invoice_open', cr)
                    if partner.openinvoice_del:
                            invoice_line=invoice_line_obj.search(cr, uid, [('invoice_id','=', partner.openinvoice_id)])
                            if invoice_line:
                                invoice_line_rec=invoice_line_obj.browse(cr, uid, invoice_line[0])
                                membership_line_obj=self.pool.get('membership.membership_line')
                                membership_line = membership_line_obj.search(cr, uid, [('account_invoice_line','=',invoice_line_rec.id)])
                                if membership_line:
                                    membership_line_obj.unlink(cr, uid, membership_line[0])

                                refund_wiz = self.pool.get('account.invoice.refund')

                                vals={}
                                vals['filter_refund'] = 'cancel'
                                vals['description'] = 'Invoice cancelled from bank statement'
                                journal_ids = self.pool.get('account.journal').search(cr, uid, [('code','=','LIDC')])
                                if not journal_ids or len(journal_ids) > 1:
                                    raise osv.except_osv(_('Error!'), _('No refund journal could be found.'))
                                vals['journal_id'] = journal_ids[0]
                                vals['date'] = time.strftime('%Y-%m-%d')
                                vals['period'] = self.pool.get('account.period').find(cr, uid, dt=vals['date'], context=context)[0]

                                refund_wiz_id = self.pool.get('account.invoice.refund').create(cr, uid, vals, context=context)

                                context['skip_write'] = True
                                context['active_ids'] = [partner.openinvoice_id]
                                refund_res = self.pool.get('account.invoice.refund').compute_refund(cr, uid, [refund_wiz_id], mode='cancel', context=context)

                cr.commit()

                if 'stmt_id' in context and context['stmt_id']:
                    stmt_obj = self.pool.get('account.bank.statement.line')
                    stmt_ids = stmt_obj.search(cr, uid, [('id','=',context['stmt_id'])])
                    stmt_obj.write(cr, uid, stmt_ids, {
                        'partner_id2': partner_id,
                        'amount': amount_inv,
                    }, context=context)
                    stmt = stmt_obj.browse(cr, uid, stmt_ids[0])

                    mvl_obj = self.pool.get('account.move.line')
                    #mvl_ids = mvl_obj.search(cr, uid, [('partner_id','=', partner_id), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)])
                    invoice = invoice_obj.browse(cr, uid, invoice_id)
                    mvl_ids = mvl_obj.search(cr, uid, [('move_id','=', invoice.move_id.id), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)]) 
                    if mvl_ids:
                        mvl = mvl_obj.browse(cr, uid, mvl_ids[0])

                        account = mvl.account_id.id
                        stmt_obj.write(cr, uid, stmt_ids, {
                            'account_id': account,
                        }, context=context)

                        reconcile = mvl.id
                        transaction_type = 'customer'                                    

                        voucher_vals = {
                            'type': transaction_type == 'supplier' and 'payment' or 'receipt',
                            'name': mvl.move_id.name,
                            'partner_id': partner_id,
                            'journal_id': stmt.statement_id.journal_id.id,
                            'account_id': stmt.statement_id.journal_id.membership_account_id.id,
                            'company_id': mvl.move_id.company_id.id,
                            'currency_id': mvl.move_id.journal_id.currency.id,
                            'date': mvl.date,
                            'amount': amount_inv,
                            'line_amount': amount_inv,
                            'period_id': stmt.statement_id.period_id.id,
#                            'invoice_id': invoice_id,
                        }
                        context['move_line_ids'] = [mvl.id]
                        context['invoice_id'] = invoice_id
                        voucher_vals.update(self.pool.get('account.voucher').onchange_partner_id(cr, uid, [],
                            partner_id = partner_id,
                            journal_id = stmt.statement_id.journal_id.id,
                            amount = amount_inv,
                            currency_id = mvl.move_id.journal_id.currency.id,
                            ttype = transaction_type == 'supplier' and 'payment' or 'receipt',
                            date = mvl.date,
                            context = context
                        )['value'])
                        line_drs = []
                        for line_dr in voucher_vals['line_dr_ids']:
                            line_drs.append((0, 0, line_dr))
                        voucher_vals['line_dr_ids'] = line_drs
                        line_crs = []
                        for line_cr in voucher_vals['line_cr_ids']:
                            line_crs.append((0, 0, line_cr))
                        voucher_vals['line_cr_ids'] = line_crs
                        voucher_id = self.pool.get('account.voucher').create(cr, uid, voucher_vals, context=context)

                        stmt_obj.write(cr, uid, stmt_ids, {
                            'voucher_id': voucher_id,
                        }, context=context)

            if partner.donation_partner:
                create_donation = True

                stmt_obj = self.pool.get('account.bank.statement.line')
                stmt_ids = stmt_obj.search(cr, uid, [('id','=',context['stmt_id'])])
                stmt = stmt_obj.browse(cr, uid, stmt_ids[0])

                partner_rec = partner_obj.browse(cr, uid, partner_id)

                analytic_dimension_1_id = None
                analytic_dimension_2_id = None
                analytic_dimension_3_id = None
                if partner.analytic_account_id.dimension_id.sequence == 1:
                    analytic_dimension_1_id = partner.analytic_account_id.id
                    if partner.analytic_account_id.default_dimension_2_id:
                        analytic_dimension_2_id = partner.analytic_account_id.default_dimension_2_id.id
                    if partner.analytic_account_id.default_dimension_3_id:
                        analytic_dimension_3_id = partner.analytic_account_id.default_dimension_3_id.id
                if partner.analytic_account_id.dimension_id.sequence == 2:
                    analytic_dimension_2_id = partner.analytic_account_id.id
                    if partner.analytic_account_id.default_dimension_1_id:
                        analytic_dimension_1_id = partner.analytic_account_id.default_dimension_1_id.id
                    if partner.analytic_account_id.default_dimension_3_id:
                        analytic_dimension_3_id = partner.analytic_account_id.default_dimension_3_id.id
                if partner.analytic_account_id.dimension_id.sequence == 3:
                    analytic_dimension_3_id = partner.analytic_account_id.id
                    if partner.analytic_account_id.default_dimension_1_id:
                        analytic_dimension_1_id = partner.analytic_account_id.default_dimension_1_id.id
                    if partner.analytic_account_id.default_dimension_2_id:
                        analytic_dimension_2_id = partner.analytic_account_id.default_dimension_2_id.id

                account_id = partner.donation_product_id.property_account_income.id or False

                quantity = 1

                if partner.membership_partner:
                    stmt_id = stmt_obj.create(cr, uid, {
                            'account_id': account_id,
                            'amount': partner.donation_amount_inv,
                            'analytic_dimension_1_id': analytic_dimension_1_id,
                            'analytic_dimension_2_id': analytic_dimension_2_id,
                            'analytic_dimension_3_id': analytic_dimension_3_id,
                            'coda_account_number': stmt.coda_account_number,
                            'company_id': stmt.company_id.id,
                            'crm_account': True,
                            'date': stmt.date,
                            'det2_ids': stmt.det2_ids,
                            'det3_ids': stmt.det3_ids,
                            'journal_id': stmt.journal_id.id,
                            'lines2_id': stmt.lines2_id.id,
                            'name': stmt.name,
                            'name_zonder_adres': stmt.name_zonder_adres,
                            'note': stmt.note,
                            'partner_id': partner_id,
                            'partner_ref': stmt.partner_ref,
                            'ref': stmt.ref,
                            'sequence': stmt.sequence,
                            'state': stmt.state,
                            'statement_id': stmt.statement_id.id,
                            'structcomm_flag': stmt.structcomm_flag,
                            'structcomm_message': stmt.structcomm_message,
                            'transaction_code': stmt.transaction_code,
                            'type': stmt.type,
                    }, context=context)
                else:
                    stmt_obj.write(cr, uid, stmt_ids, {
                            'account_id': account_id,
                            'analytic_dimension_1_id': analytic_dimension_1_id,
                            'analytic_dimension_2_id': analytic_dimension_2_id,
                            'analytic_dimension_3_id': analytic_dimension_3_id,
                            'partner_id': partner_id,
                    }, context=context)

#        return {'type':'ir.actions.act_window_close', 'tag':'reload'}
        if create_membership and create_donation:
#             return {'type': 'ir.actions.client', 'tag':'reload'}
             return {'type': 'ir.actions.act_window_close'}
        else:
            return {'type':'ir.actions.act_window_close'}

bank_statement_create_partner()

class product_product(osv.osv):
    _inherit = 'product.product'

    _columns = {
        'donation_product_bank_stmt': fields.boolean('Gift Rekeninguitreksel'),
    }

product_product()

def _format_iban(iban_str):
    '''
    This function removes all characters from given 'iban_str' that isn't a alpha numeric and converts it to upper case.
    '''
    res = ""
    if iban_str:
        for char in iban_str:
            if char.isalnum():
                res += char.upper()
    return res

class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"

    def create(self, cr, uid, vals, context=None):
        res = super(res_partner_bank, self).create(cr, uid, vals, context)
        if (vals.get('state',False)=='iban') and vals.get('acc_number', False):
            vals['acc_number'] = _format_iban(vals['acc_number'])
            self.write(cr, uid, [res], {'acc_number': vals['acc_number']}, context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res= super(res_partner_bank, self).write(cr, uid, ids, vals, context)
        if vals.get('acc_number', False):
            for rpb in ids:
                acc_number = _format_iban(vals['acc_number'])
                sql_stat = "update res_partner_bank set acc_number = '%s' where id = %d" % (acc_number, rpb,)
                cr.execute(sql_stat)
                cr.commit()
                del vals['acc_number']       
        return res

res_partner_bank()

def _format_vat(vat_str):
    '''
    This function removes all characters from given 'vat_str' that isn't a alpha numeric and converts it to upper case.
    '''
    res = ""
    if vat_str:
        for char in vat_str:
            if char.isalnum():
                res += char.upper()
    return res

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def create(self, cr, uid, vals, context=None):
        res = super(res_partner, self).create(cr, uid, vals, context)
        if vals.get('vat', False):
            vals['vat'] = _format_vat(vals['vat'])
            self.write(cr, uid, [res], {'vat': vals['vat']}, context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        res= super(res_partner, self).write(cr, uid, ids, vals, context)
        if vals.get('vat', False):
            for rp in ids:
                vat = _format_iban(vals['vat'])
                sql_stat = "update res_partner set vat = '%s', vat_subjected = 'True' where id = %d" % (vat, rp,)
                cr.execute(sql_stat)
                cr.commit()
                del vals['vat']       
        return res

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
