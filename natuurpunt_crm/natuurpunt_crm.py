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
from datetime import datetime
from datetime import time
from datetime import date
import re

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(res_partner,self).name_get(cr, uid, ids, context=context)
        res2 = []
        for partner_id, name in res:
            record = self.read(cr, uid, partner_id, ['id','name'], context=context)
            if record['id']:
                idn = str(record['id'])
            else:
                idn = ''
            if record['name']:
                name2 = record['name']
            else:
                name2 = ''
            new_name = '[' + idn + '] ' + name2
            res2.append((partner_id, new_name))
        return res2

    def _function_create_date(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):
            if partner.id:
                sql_stat = '''select create_date from res_partner where id =  %d''' % (partner.id, )
                cr.execute(sql_stat)
                sql_res = cr.dictfetchone()
                if sql_res['create_date']:
                    res[partner.id] = sql_res['create_date']
                else:
                    res[partner.id] = None
        return res

    def _function_write_date(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):
            if partner.id:
                sql_stat = '''select write_date from res_partner where id =  %d''' % (partner.id, )
                cr.execute(sql_stat)
                sql_res = cr.dictfetchone()
                if sql_res['write_date']:
                    res[partner.id] = sql_res['write_date']
                else:
                    res[partner.id] = None
        return res

    def _function_name_disp(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for partner in self.browse(cr, uid, ids):
            if partner.id:
                res[partner.id] = ''
                if partner.first_name:
                    res[partner.id] = partner.first_name + ' '
                if partner.last_name:
                    res[partner.id] = res[partner.id] + partner.last_name
        return res

    _columns = {
        'email': fields.char('Email', size=240, help = 'Opgelet: dit privé mail is nodig om in te loggen op de natuurpunt site en mag niet zomaar gewijzigd worden!'),
        'last_name': fields.char('Familienaam', len=64),
        'first_name': fields.char('Voornaam', len=64),
        'gender': fields.selection([('M','Man'),('V','Vrouw'),('O','Ongekend')], string='Geslacht', size=1),
        'birthday': fields.date('Geboortedatum'),
		'address_origin_id': fields.many2one('res.partner.address.origin', 'Herkomst Adres', select=True),
		'membership_origin_id': fields.many2one('res.partner.membership.origin', 'Herkomst Lidmaatschap', select=True,domain=['|',('date_end','>','now()'),('date_end','=',False)]),
		'address_state_id': fields.many2one('res.partner.address.state', 'Status', select=True),
		'address_history_ids': fields.one2many('res.partner.address.history', 'partner_id', 'Verhuishistoriek'),
        'tax_certificate': fields.boolean('Fiscaal attest'),
        'thanks_letter': fields.boolean('Bedankbrief'),
        'expense_note': fields.boolean('Onkostennota gewenst'),
        'npca_id': fields.integer('NPCA id', select=True),
        'modulas_id': fields.integer('Modulas id', select=True),
        'npca_char': fields.char('NPCA',len=12),
        'address_id': fields.char('Adres id', len=16, select=True),
        'person': fields.boolean('Persoon'),
        'vip': fields.boolean('VIP'),
        'phone_work': fields.char('Telefoon werk', len=32),
        'email_work': fields.char('Email werk', len=128, help = "Opgelet: voor professionele medewerkers is het werkmail nodig om in te loggen op NP applicaties. Een @natuurpunt.be adres is vereist!"),
        'year_birth': fields.integer('Geboortejaar'),
        'national_id_nbr': fields.char('Rijksregisternr.', len=16),
        'crab_used': fields.boolean('CRAB-code'),
		'relation_partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'deceased': fields.boolean('Overleden'),
        'email_website': fields.char('Email website', len=128),
        'password_website': fields.char('Paswoord website', len=128),
        'department_id': fields.many2one('res.partner', 'Afdeling woonplaats', select=True),
        'department_choice_id': fields.many2one('res.partner', 'Afdeling eigen keuze', select=True),
        'no_department': fields.boolean('Geen afdeling'),
#        'department_choice': fields.boolean('Afdeling eigen keuze'),
        'np_create_date': fields.function(_function_create_date, string='Aanmaakdatum', type='date'),
        'np_write_date': fields.function(_function_write_date, string='Wijzigdatum', type='date'),
        'postbus_nbr': fields.char('Postbus', len=16),
        'address_origin_date': fields.date('Datum Herkomst Adres'),
		'interest_ids': fields.many2many('res.partner.interest', 'res_partner_interest_rel_rel', 'partner_id', 'interest_id', 'Interessegebieden'),
		'recruiting_member_id': fields.many2one('res.partner', 'Wervend Lid', select=True),
		'recruiting_organisation_id': fields.many2one('res.partner', 'Wervende Organisatie', select=True),
		'corporation_type_id': fields.many2one('res.partner.corporation.type', 'Type Rechtspersoon', select=True),
        'no_magazine': fields.boolean('Geen Tijdschrift'),
        'crm_payment_ids': fields.one2many('account.bank.statement.line', 'partner_id', 'CRM Betalingen', readonly=True, domain=[('crm_account','=',True)]),
        'crm_move_ids': fields.one2many('account.move.line', 'partner_id', 'CRM Boekingen', readonly=True, domain=[('account_id','in',(1914,2556,3308,3934,4100,1222,1836,2513,3285,3917,4036,4039,4114,4204))]),
		'partner_state_id': fields.many2one('res.partner.state', 'Partner Status', select=True),
        'payment_history_ids': fields.one2many('res.partner.payment.history', 'partner_id', 'NPCA Betalingen', readonly=True),
		'deceased_partner_id': fields.many2one('res.partner', 'Overdracht Naar', select=True),
        'uit_id': fields.char('Uit ID'),
        'name_disp': fields.function(_function_name_disp, string='Name', type='char'),
        'membership_nbr': fields.char('Lidnummer'),
        'membership_nbr_set': fields.boolean('Lidnummer_set'),
        'membership_nbr_num': fields.integer('Lidnummer_num'),
        'opt_out': fields.boolean('Uitschrijven email'),
        'opt_out_letter': fields.boolean('Uitschrijven brief'),
        'member_recruit_member': fields.boolean('Leden Werven Leden'),
		'country': fields.related('country_id', type='many2one', relation='res.country', string='Country Depr',
			deprecated="This field will be removed as of OpenERP 7.1, use country_id instead"),
		'no_address': fields.boolean('Geen addres'),
    }

    _defaults = {
        'tax_certificate': True,
        'crab_used': True,
        'free_member': False,
        'out_inv_comm_type': 'bba',
        'out_inv_comm_algorithm': 'partner_ref',
        'opt_out': False,
        'opt_out_letter': False,
        'no_address': False,
    }

    def onchange_name(self, cr, uid, ids, first_name, last_name, context=None):
        res = {}
        if not first_name:
            if last_name == '':
                res['name'] = None
            else:
                res['name'] = last_name
        else:
            if not last_name:
                res['name'] = first_name
            else:
                res['name'] = first_name + ' ' + last_name
        res['name_disp'] = res['name']
        return {'value':res}

    def onchange_deceased(self, cr, uid, ids, deceased, relation_partner_id, context=None):
        res = {}
        if deceased:
            res['active'] = False
            res['deceased_partner_id'] = relation_partner_id
        else:
            res['active'] = True
            res['deceased_partner_id'] = None
        return {'value':res}

    def onchange_email(self, cr, uid, ids, email, context=None):
        res = {}
        warning = ''
        if context and 'web' in context:
            web = True
        else:
            web = False
        if email:
#            match = re.search(r'\w+@\w+\.\w+',email)
            match = re.search(r'[-\w]+@[-\w]+\.\w+',email)
            if not match:
                warning = email
        if not (warning == ''):
            raise osv.except_osv(_('Ongeldig e-mail adres:'), _(warning))
            return False

        if not ids:
            sql_stat = "select id, name, ref from res_partner where upper(email) = upper('%s') or upper(email_work)= upper('%s')" % (email, email, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if warning == '':
                    warning = sql_res['name']
                else:
                    warning = warning + sql_res['name']
                if sql_res['id']:
                    warning = warning + ' (' + str(sql_res['id']) + ')'
                warning = warning + ''' 
'''
        else:
            for id_member in ids:
                sql_stat = "select id, name, ref from res_partner where upper(email) = upper('%s') or upper(email_work)= upper('%s')" % (email, email, )
                cr.execute(sql_stat)
                for sql_res in cr.dictfetchall():
                    if not(id_member == sql_res['id']):
                        if warning == '':
                            warning = sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                        else:
                            warning = warning + ', ' + sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                        warning = warning + ''' 
'''

        if not (warning == '') and not web:
            warning_msg = { 
                    'title': _('Warning!'),
                    'message': _('''De volgende contacten zijn reeds geregistreerd met dit email-adres: 
%s''' % (warning))
                }   
            return {'warning': warning_msg}
        return res

    def onchange_phone(self, cr, uid, ids, phone, context=None):
        res = {}
        warning = ''
        if phone:
            match = False
            if re.search(r'0\d{1} \d{3} \d{2} \d{2}',phone):
                match = True
            if re.search(r'0\d{2} \d{2} \d{2} \d{2}',phone):
                match = True
            if phone[:1] == '+' and re.search(r'\d{2} \w+',phone[1:]):
                match = True
            if not match:
                warning = phone + ' moet 09 999 99 99 of 099 99 99 99 of +99 xxxxxx zijn'
        if not (warning == ''):
            raise osv.except_osv(_('Ongeldig telefoonnummer:'), _(warning))
            return False
        return True

    def onchange_mobile(self, cr, uid, ids, mobile, context=None):
        res = {}
        warning = ''
        if mobile:
            match = False
            if re.search(r'04\d{2} \d{2} \d{2} \d{2}',mobile):
                match = True
            if mobile[:1] == '+' and re.search(r'\d{2} \w+',mobile[1:]):
                match = True
            if not match:
                warning = mobile + ' moet 0499 99 99 99 of +99 xxxxxx zijn'
        if not (warning == ''):
            raise osv.except_osv(_('Ongeldig GSM nummer:'), _(warning))
            return False
        return True

    def onchange_future_date(self, cr, uid, ids, input_date, context=None):
        res = {}
        warning = ''
        if input_date > datetime.today().strftime('%Y-%m-%d'):
                warning = 'Datum mag niet in de toekomst liggen'
        if not (warning == ''):
            raise osv.except_osv(_('Fout: '), _(warning))
            return False
        return True

    def onchange_organisation_type(self, cr, uid, ids, organisation_type_id, context=None):
        res = {}
        warning = 'Organisatietype wordt aangepast'
        if not (warning == ''):
            raise osv.except_osv(_('Let op: '), _(warning))
            return False
        return True

    def onchange_crab_used(self, cr, uid, ids, crab_used, context=None):
        res = {}
#         print'ON CHANGE CRAB USED:',crab_used
        res['street'] = ''
        res['street2'] = ''
        res['zip'] = ''
        res['city'] = ''
        res['street_nbr'] = ''
        res['street_bus'] = ''
        res['postbus_nbr'] = ''
        res['street_id'] = False
        res['zip_id'] = False
        res['state_id'] = False
# Fix ticket #1929, commented out next two lines
#         if not crab_used:
#             res['country_id'] = False
        return {'value':res}

    def onchange_no_address(self, cr, uid, ids, no_address, country_id, context=None):
		res = {}
		if not(no_address) and country_id == 21:
			res['crab_used'] = True
		return {'value': res}

    def onchange_country(self, cr, uid, ids, country_id, no_address, context=None):
        res = {}
        if country_id == 21 and no_address == False:
            res['crab_used'] = True
        else:
            res['crab_used'] = False
        return {'value':res}

    def onchange_relation_id(self, cr, uid, ids, relation_partner_id, street_id, street_nbr, street_bus, context=None):
        res = {}
        sql_stat = "select case when relation_partner_id IS NULL then 0 else 1 end as relation_found from res_partner where id = %d" % (relation_partner_id )
#         print sql_stat
        cr.execute(sql_stat)
        warning = ''
        for sql_res in cr.dictfetchall():
            print 'RESULT SQL:', sql_res['relation_found']
            if sql_res['relation_found'] == 1:
                warning = 'De gekozen relatie heeft reeds een partner'
        if warning == '':
            sql_stat = "select street_id, street_nbr, street_bus from res_partner where id = %d" % (relation_partner_id)
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if street_id and not(street_id == sql_res['street_id']):
                    warning = 'Partners hebben verschillende adressen'
                if street_nbr and not(street_nbr == sql_res['street_nbr']):
                    warning = 'Partners hebben verschillende adressen'
                if street_bus and not(street_bus == sql_res['street_bus']):
                    warning = 'Partners hebben verschillende adressen'
        if not (warning == ''):
            res['value'] = {}
            res['value']['relation_partner_id'] = False
            res['warning'] = {}
            res['warning']['title'] = 'FOUT'
            res['warning']['message'] = warning 
        return res

    def update_state_id(self,vals,zip_id,cr):
        if zip_id:
            sql_stat = "select state_id from res_country_city where id = %d" % (zip_id, )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if sql_res['state_id']:
                    vals['state_id'] = sql_res['state_id']
        return vals
    
    def onchange_street_id(self, cr, uid, ids, zip_id, street_id, street_nbr, street_bus, context=None):
        res = super(res_partner, self).onchange_street_id(cr, uid, ids, zip_id, street_id, street_nbr, street_bus, context=context)
        id_member = 0
        warning = ''
        if context and 'web' in context:
            web = True
        else:
            web = False          
        res['value'] = self.update_state_id(res['value'],zip_id,cr)
#         if zip_id:
#             sql_stat = "select state_id from res_country_city where id = %d" % (zip_id, )
#             cr.execute(sql_stat)
#             for sql_res in cr.dictfetchall():
#                 if sql_res['state_id']:
#                     res['value']['state_id'] = sql_res['state_id']
        if street_nbr == False:
            street_nbr = ''
        if street_bus == False:
            street_bus = ''
        if not ids:
            sql_stat = "select id, name, ref from res_partner where zip_id = %d and street_id = %d and (street_nbr = '%s' or street_nbr IS NULL) and (street_bus = '%s' or street_bus IS NULL)" % (zip_id, street_id, street_nbr, street_bus, )
            print sql_stat
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if warning == '':
                    warning = sql_res['name']
                else:
                    warning = warning + sql_res['name']
                if sql_res['id']:
                    warning = warning + ' (' + str(sql_res['id']) + ')'
                warning = warning + ''' 
'''
        for id_member in ids:
            sql_stat = "select id, name, ref from res_partner where zip_id = %d and street_id = %d and (street_nbr = '%s' or street_nbr IS NULL) and (street_bus = '%s' or street_bus IS NULL)" % (zip_id, street_id, street_nbr, street_bus, )
            print sql_stat
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                if not(id_member == sql_res['id']):
                    if warning == '':
                        warning = sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                    else:
                        warning = warning + ', ' + sql_res['name'] + ' (' + str(sql_res['id']) + ')'
                    warning = warning + ''' 
'''

        if not (warning == '') and not web:
            warning_msg = { 
                    'title': _('Warning!'),
                    'message': _('De volgende contacten zijn reeds geregistreerd op dit adres: %s'%(warning))
                }   
            return {'value': res['value'], 'warning': warning_msg}
        return res

    def onchange_postbus_nbr(self, cr, uid, ids, postbus_nbr, context=None):
        res = {}
        if postbus_nbr != '':
            if postbus_nbr != False:
                res['street_id'] = False
                res['street_nbr'] = False
                res['street_bus'] = False
                res['street'] = 'Postbus ' + postbus_nbr
        return {'value':res}

    def onchange_membership_origin(self, cr, uid, ids, membership_origin_id, context=None):
        res = {}
        if membership_origin_id:
            sql_stat = "select member_recruit_member from res_partner_membership_origin where id = %d" % (membership_origin_id, )
            print sql_stat
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                res['member_recruit_member'] = sql_res['member_recruit_member']
        else:
            res['member_recruit_member'] = False
        return {'value':res}

    def create(self, cr, uid, vals, context=None):
        if 'zip_id' in vals and vals['zip_id'] and 'state_id' not in vals:
            vals = self.update_state_id(vals,vals['zip_id'],cr)
        if 'organisation_type_id' in vals and vals['organisation_type_id']:
            vals['crab_used'] = False
            vals['country_id'] = 21
            vals['no_address'] = True
        if 'membership_nbr' in vals:
            vals['membership_nbr_set'] = True
            if vals['membership_nbr']:
                vals['membership_nbr_num'] = int(vals['membership_nbr'])
        if 'birthday' in vals and vals['birthday']:
            vals['year_birth'] = vals['birthday'][:4]
        if 'zip_id' in vals and vals['zip_id']:
            department_id = None
            sql_stat = 'select partner_id from res_organisation_city_rel, res_partner where res_partner.id = partner_id and organisation_type_id = 1 and res_organisation_city_rel.zip_id = %d' % (vals['zip_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                department_id = sql_res['partner_id']
            vals['department_id'] = department_id
        if 'last_name' in vals and vals['last_name']:
            if 'first_name' in vals and vals['first_name']:
                vals['name'] = vals['first_name'] + ' ' + vals['last_name']
            else:
                vals['name'] = vals['last_name']
        else:
            if 'first_name' in vals and vals['first_name']:
                vals['name'] = vals['first_name']
        vals['free_member'] = False

        res = super(res_partner, self).create(cr, uid, vals, context=context)
        prc = self.browse(cr, uid, res)

        if prc.street:
            province = None
            if prc.zip_id.state_id:
                province = prc.zip_id.state_id.name
            rec = self.pool.get('res.partner.address.history')
            rec_id = rec.create(cr, uid, {
#                'date_move': datetime.today().strftime('%Y-%m-%d'),
                'user_id': uid,
                'partner_id': prc.id,
                'name': prc.name,
                'ref': prc.ref,
                'street': prc.street,
                'street2': prc.street2,
                'zip': prc.zip,
                'city': prc.city,
                'state': province,
                'country_id': prc.country_id.id,
            },context=context)
        if 'relation_partner_id' in vals:
            sql_stat = "update res_partner set relation_partner_id = %d where id = %d" % (prc.id, vals['relation_partner_id'], )
            print sql_stat
            cr.execute(sql_stat)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if 'zip_id' in vals and vals['zip_id'] and 'state_id' not in vals:
            vals = self.update_state_id(vals,vals['zip_id'],cr)
        if 'membership_nbr' in vals:
            vals['membership_nbr_set'] = True
            vals['membership_nbr_num'] = int(vals['membership_nbr'])
        if 'birthday' in vals and vals['birthday']:
            vals['year_birth'] = vals['birthday'][:4]
        if 'zip_id' in vals and vals['zip_id']:
            department_id = None
            sql_stat = 'select partner_id from res_organisation_city_rel where zip_id = %d' % (vals['zip_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                department_id = sql_res['partner_id']
            vals['department_id'] = department_id
        elif 'state_id' in vals:
            vals['department_id'] = None
        relation_partner_id = 0
        if 'relation_partner_id' in vals:
            for partners in ids:
                sql_stat = 'select case when not (relation_partner_id IS NULL) then relation_partner_id else 0 end as relation_partner_id from res_partner where id = %d' % (partners, )
                print sql_stat
                cr.execute(sql_stat)
                for sql_res in cr.dictfetchall():
                    relation_partner_id = sql_res['relation_partner_id']

        if 'street' in vals or 'street2' in vals or 'zip' in vals or 'city' in vals or 'state_id' in vals or 'country_id' in vals:
            sql_stat = 'select id from res_partner_address_state where valid_address = True'
            print sql_stat
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['address_state_id'] = sql_res['id']

        if 'member_lines' in vals:
            context['skip_write'] = True
# 473        
        if 'zip_ids' in vals:
            old = self.browse(cr, uid, ids)[0]
            print 'old', old
            for old in self.browse(cr, uid, ids):
                print 'old', old
                print 'old zip_ids', old.zip_ids
# 473            
 
        res = super(res_partner, self).write(cr, uid, ids, vals, context=context)
        if not isinstance(ids, list):
            ids = [ids]
        for prc in self.browse(cr, uid, ids):
# 473        
            if 'zip_ids' in vals:
                print 'organization', prc.organisation_type_id.id
                if prc.organisation_type_id.id == 1:
                    print 'prc', prc.zip_ids
                    print 'old', old.zip_ids
                    
                    for rel in prc.zip_ids:
                        if not(rel in old.zip_ids):
                            sql_stat = 'update res_partner set department_id = %d where zip_id = %d' % (prc.id, rel.id ,)
                            print sql_stat
                            cr.execute(sql_stat)
# 473            
            if 'relation_partner_id' in vals and not (relation_partner_id == 0):
                sql_stat = "update res_partner set relation_partner_id = NULL where id = %d" % (relation_partner_id, )
                cr.execute(sql_stat)
            if 'relation_partner_id' in vals and vals['relation_partner_id']:
                sql_stat = "update res_partner set relation_partner_id = %d where id = %d" % (prc.id, vals['relation_partner_id'], )
                cr.execute(sql_stat)

            if 'street' in vals or 'street2' in vals or 'name' in vals or 'zip' in vals or 'city' in vals or 'state_id' in vals or 'country_id' in vals or 'department_id' in vals or 'department_choice_id' in vals or 'no_department' in vals:
                if prc.zip_id:
                    prov = prc.zip_id.state_id.name
                else:
                    prov = None
                if 'street' in vals or 'street2' in vals or 'name' in vals or 'zip' in vals or 'city' in vals or 'state_id' in vals or 'country_id' in vals:
                    rec = self.pool.get('res.partner.address.history')
                    rec_id = rec.create(cr, uid, {
#                        'date_move': datetime.today().strftime('%Y-%m-%d'),
                        'user_id': uid,
                        'partner_id': prc.id,
                        'name': prc.name,
                        'ref': prc.ref,
                        'street': prc.street,
                        'street2': prc.street2,
                        'zip': prc.zip,
                        'city': prc.city,
                        'state': prov,
                        'country_id': prc.country_id.id,
                    },context=context)

                rel_partner_id = 0
                rel_partner_name = prc.name
                if 'relation_partner_id' in vals and vals['relation_partner_id']:
                    rel_partner_id = vals['relation_partner_id']
                if prc.relation_partner_id.id:
                    rel_partner_id = prc.relation_partner_id.id
                    rel_partner_name = prc.relation_partner_id.name
                
                if rel_partner_id != 0:
                    if prc.street:
                        street = prc.street.replace( "'", '"')
                    else:
                        street = ''
                    if prc.street2:
                        street2 = prc.street2.replace( "'", '"')
                    else:
                        street2 = ''
                    if prc.zip:
                        zip = prc.zip
                    else:
                        zip = ''
                    if prc.city:
                        city = prc.city
                    else:
                        city = ''
                    if prc.street_nbr:
                        street_nbr = prc.street_nbr
                    else:
                        street_nbr = ''
                    if prc.street_bus:
                        street_bus = prc.street_bus
                    else:
                        street_bus = ''
                    if prc.postbus_nbr:
                        postbus_nbr = prc.postbus_nbr
                    else:
                        postbus_nbr = ''
                    if prc.department_choice_id:
                        depchoice = prc.department_choice_id.id
                    else:
                        depchoice = None
                    if prc.department_id:
                        depid = prc.department_id.id
                    else:
                        depid = None
                    if prc.no_department:
                        nodep = 'True'
                    else:
                        nodep = 'False'
                    if prc.state_id:
                        prov = prc.state_id.id
                        provname = prc.state_id.name
                    else:
                        prov = None
                        provname = None
                    sql_stat = '''update res_partner set 
                        crab_used = True,
                        street = '%s',
                        street2 = '%s',
                        zip = '%s',
                        city = '%s', 
                        country_id = %d, 
                        zip_id = NULL, 
                        street_id = NULL,
                        street_nbr = '%s',
                        street_bus = '%s',
                        postbus_nbr = '%s',
                        department_id = NULL,
                        state_id = NULL,
                        no_department = %s
                    where id = %d''' % (street, street2, zip, city, prc.country_id.id, street_nbr, street_bus, postbus_nbr, nodep, rel_partner_id, )
                    cr.execute(sql_stat)
                    if prc.department_choice_id:
                        sql_stat = '''update res_partner set 
                            department_choice_id = %d
                        where id = %d''' % (prc.department_choice_id.id, rel_partner_id, )
                        cr.execute(sql_stat)
                    if prc.state_id:
                        sql_stat = '''update res_partner set
                            state_id = %d
                        where id = %d''' % (prov, rel_partner_id, )
                        cr.execute(sql_stat)
                    if prc.zip_id:
                        sql_stat = '''update res_partner set
                            zip_id = %d
                        where id = %d''' % (prc.zip_id.id, rel_partner_id, )
                        cr.execute(sql_stat)
                    if prc.street_id:
                        sql_stat = '''update res_partner set
                            street_id = %d
                        where id = %d''' % (prc.street_id.id, rel_partner_id, )
                        cr.execute(sql_stat)
                    if prc.department_id:
                        sql_stat = '''update res_partner set
                            department_id = %d
                        where id = %d''' % (prc.department_id.id, rel_partner_id, )
                        cr.execute(sql_stat)
                    if not prc.crab_used:
                        sql_stat = '''update res_partner set
                            crab_used = False
                        where id = %d''' % (rel_partner_id, )
                        cr.execute(sql_stat)
                    if 'street' in vals or 'street2' in vals or 'zip' in vals or 'city' in vals or 'state' in vals or 'country_id' in vals:
                        rec = self.pool.get('res.partner.address.history')
                        rec_id = rec.create(cr, uid, {
#                        'date_move': datetime.today().strftime('%Y-%m-%d'),
                            'user_id': uid,
                            'partner_id': rel_partner_id,
                            'name': rel_partner_name,
                            'ref': prc.ref,
                            'street': prc.street,
                            'street2': prc.street2,
                            'zip': prc.zip,
                            'city': prc.city,
                            'state': provname,
                            'country_id': prc.country_id.id,
                        },context=context)

        return res

# Temporary solution for memberships without invoices
# Controleren met Fabian waarom dit niet werkt
#    def _membership_state(self, cr, uid, ids, name, args, context=None):
#        res = {}
#        for id in ids:
#            res[id] = 'none'
#        today = datetime.today().strftime('%Y-%m-%d')
#        for id in ids:
#            partner_data = self.browse(cr, uid, id, context=context)
#            if partner_data.membership_cancel and today > partner_data.membership_cancel:
#                res[id] = 'canceled'
#                continue
#            if partner_data.membership_stop and today > partner_data.membership_stop:
#                res[id] = 'old'
#                continue
#            s = 4
#            if partner_data.member_lines:
#                res[id] = 'paid'
#            if partner_data.free_member and s!=0:
#                res[id] = 'free'
#        print res[id], " ", partner_data.npca_id
#        return res

res_partner() 

class res_partner_address_origin(osv.osv):
    _name = 'res.partner.address.origin'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
		'address_origin_category_id': fields.many2one('res.partner.address.origin.category', 'Categorie Herkomst', select=True),
    }

res_partner_address_origin()

class res_partner_address_origin_category(osv.osv):
    _name = 'res.partner.address.origin.category'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
    }

res_partner_address_origin_category()

class res_partner_membership_origin(osv.osv):
    _name = 'res.partner.membership.origin'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
        'member_recruit_member': fields.boolean('Leden Werven Leden'),
        'date_end': fields.date('Einddatum'),
		'membership_origin_category_id': fields.many2one('res.partner.membership.origin.category', 'Categorie Herkomst', select=True),
    }

res_partner_membership_origin()

class res_partner_membership_origin_category(osv.osv):
    _name = 'res.partner.membership.origin.category'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
    }

res_partner_membership_origin_category()

class res_partner_interest(osv.osv):
    _name = 'res.partner.interest'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
    }

res_partner_interest()

class res_partner_corporation_type(osv.osv):
    _name = 'res.partner.corporation.type'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
    }

res_partner_corporation_type()

class res_partner_address_state(osv.osv):
    _name = 'res.partner.address.state'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
        'valid_address': fields.boolean('Valid Address'),
    }

res_partner_address_state()

class res_partner_address_history(osv.osv):
    _name = 'res.partner.address.history'

    _order = 'date_move desc, id desc'

    _columns = {
        'date_move': fields.date('Verhuisdatum'),
		'user_id': fields.many2one('res.users', 'Gebruiker', select=True),
		'partner_id': fields.many2one('res.partner', 'Relatie', select=True),
        'name': fields.char('Naam', len=128),
        'ref': fields.char('Code', len=32),
        'street': fields.char('Straat', len=64),
        'street2': fields.char('Straat(2)', len=64),
        'zip': fields.char('Postcode', len=64),
        'city': fields.char('Gemeente', len=64),
        'state': fields.char('State', len=64),
        'country_id': fields.many2one('res.country', 'Land', select=True),
    }

    _defaults = {
        'date_move': lambda *a: datetime.today().strftime('%Y-%m-%d'),
    }
res_partner_address_history()

class membership_membership_line(osv.osv):
    _inherit = 'membership.membership_line'

    _columns = {
        'reason_end_membership': fields.char('Reden stopzetting', len=64),
    }

membership_membership_line()

class res_partner_state(osv.osv):
    _name = 'res.partner.state'

    _columns = {
        'name': fields.char('Name', len=64),
        'ref': fields.char('Code', len=32),
    }

res_partner_state()

class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    def _function_account_type(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = False
            if line.id:
                if line.account_id.code == '730000' or line.account_id.code == '732000' or line.account_id.code == '732100' or line.account_id.code == '000000':
                    res[line.id] = True
        return res

    _columns = {
        'crm_account': fields.function(_function_account_type, string='CRM Rekening', type='boolean', store=True),

    }

account_bank_statement_line()

class res_partner_payment_history(osv.osv):
    _name = 'res.partner.payment.history'

    _columns = {
    	'partner_id': fields.many2one('res.partner', 'Partner', select=True, ondelete='restrict'),
	    'description': fields.char('Omschrijving'),
	    'date': fields.date('Datum'),
	    'nbr_payment': fields.char('Uitrekselnr.'),
	    'sequence': fields.integer('Volgnr.'),
	    'payment_method': fields.char('Betaalwijze'),
	    'amount': fields.float('Bedrag'),
	    'mandate_nbr': fields.char('Domicilieringsnr.'),
	    'project_nbr': fields.char('Projectnr'),
	    'cost_center': fields.char('Kostenplaats'),
	    'refused': fields.boolean('Geweigerd'),
        'acc_number': fields.char('Rekeningnr.'),
    }

    _order = 'date desc, id desc'

res_partner_payment_history()

class account_account(osv.osv):
    _inherit = 'account.account'

    def __compute(self, cr, uid, ids, field_names, arg=None, context=None, query='', query_params=()):
        for id in ids:
            print id
            res[id] = 0.00

account_account()

#class account_move_line(osv.osv):
#    _inherit = 'account.move.line'
#
#    def _balance(self, cr, uid, ids, name, arg, context=None):
#        return True
#
#account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
