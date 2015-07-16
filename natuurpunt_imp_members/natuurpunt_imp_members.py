#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
# 
##############################################################################
import base64
import datetime, time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools
from md5 import md5
import csv
import re
import logging

_logger = logging.getLogger(__name__)

class member_fys_file(osv.osv):
    _name = 'member.fys.file'
    _description = 'Member Fysical File'

    _columns = {
        'filemd5': fields.char('Name MD5', size=128),
        'filename': fields.char('Name', size=128),
        'files_ids': fields.one2many('member.file', 'fys_file_id', 'Member Files', ondelete='cascade'),
                }

member_fys_file()

class member_file(osv.osv):
    _name = 'member.file'
    _description = 'Member File'

    _columns = {
        'fys_file_id': fields.many2one('member.fys.file', 'Fys. File', select=True, ondelete='cascade'),
        'lines_ids': fields.one2many('member.lines', 'file_id', 'Files', ondelete='cascade'),
        'name': fields.char('Name', size=128),
        'recruiting_organisation_id': fields.many2one('res.partner', 'Wervende Organisatie', select=True),
        'membership_origin_id': fields.many2one('res.partner.membership.origin', 'Membership Origin'),
        'address_origin_id': fields.many2one('res.partner.address.origin', 'Address Origin'),
        'imported': fields.boolean('Imported'),
                }

    def process_file(self, cr, uid, vals, context=None):
        member_file_obj = self.pool.get('member.file')
        partner_obj = self.pool.get('res.partner')
        member_file = member_file_obj.browse(cr, uid, vals[0])
        for partner in member_file.lines_ids:
            if partner.to_import:
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
                if partner.recruiting_member_id:
                    recruiting_member_id = partner.recruiting_member_id.id
                else:
                    recruiting_member_id = None
                if member_file.membership_origin_id:
                    membership_origin_id = member_file.membership_origin_id.id
                else:
                    membership_origin_id = None
                if member_file.recruiting_organisation_id:
                    recruiting_organisation_id = member_file.recruiting_organisation_id.id
                else:
                    recruiting_organisation_id = None
                if member_file.address_origin_id:
                    address_origin_id = member_file.address_origin_id.id
                else:
                    address_origin_id = None
                    
                partner_id = partner_obj.create(cr, uid, {
                    'name': partner_name,
                    'first_name': partner.first_name,
                    'last_name': partner.last_name,
                    'street': street,
                    'street_nbr': partner.street_nbr,
                    'street_bus': partner.street_bus,
                    'zip': partner.zip,
                    'zip_id': partner.zip_id.id,
                    'street_id': partner.street_id.id,
                    'city': partner.city,
                    'country_id': partner.country_id.id,
                    'email': partner.email,
                    'phone': partner.phone,
                    'mobile': partner.mobile,
                    'email_work': partner.email_work,
                    'phone_work': partner.phone_work,
                    'gender': partner.gender,
                    'birthdate': partner.birthdate,
#                     'birthyear': partner.birthyear,
                    'recruiting_organisation_id': recruiting_organisation_id,
                    'recruiting_member_id': recruiting_member_id,
                    'membership_origin_id': membership_origin_id,
                    'address_origin_id': address_origin_id,
#                     'address_origin_date':
                    'lang': 'nl_BE',
                    'membership_state': 'none',
                    'membership_nbr': None,
                    'crab_used': True,
                    'bank_ids': False,
                    }, context)

        member_file_obj.write(cr, uid, vals[0], {'imported':True})
        return True

member_file()

class member_lines(osv.osv):
    _name = 'member.lines'
    _description = 'Member lines'
    
    _columns = {
        'file_id': fields.many2one('member.file', 'Member File', select=True),
        'to_import': fields.boolean('To import'),
        'first_name': fields.char('Voornaam', len=64),
        'last_name': fields.char('Familienaam', len=64),
        'street': fields.char('Straat csv', size=64),
        'street_nbr': fields.char('Nr.', size=16),
        'street_bus': fields.char('Bus', size=16),
        'zip': fields.char('Postkode csv', size=16),
        'zip_id': fields.many2one('res.country.city', 'Postkode'),
        'street_id': fields.many2one('res.country.city.street', 'Street'),
        'city': fields.char('Gemeente csv', size=64),
        'country_id': fields.many2one('res.country', 'Country'),
        'email': fields.char('Email', len=128),
        'phone': fields.char('Phone', size=32),
        'mobile': fields.char('Mobile', size=32),
        'email_work': fields.char('Email werk', len=128),
        'phone_work': fields.char('Telefoon werk', len=32),
        'gender': fields.selection([('M','Man'),('V','Vrouw'),('O','Ongekend')], string='Geslacht', size=1),
        'birthdate': fields.char('Birthdate', size=64),
        'birthyear': fields.char('Birthdate', size=64),
        'recruiting_member': fields.char('Wervend lid', size=128),
        'recruiting_member_id': fields.many2one('res.partner', 'Wervend Lid', select=True),
        'duplicate_ids': fields.many2many('res.partner', 'res_partner_import_rel', 'import_id', 'partner_id', 'Mogelijke dubbels'),
                }

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
     
    def onchange_phone_work(self, cr, uid, ids, phone_work, context=None):
        res = {}
        warning = ''
        if phone_work:
            match = False
            if re.search(r'0\d{1} \d{3} \d{2} \d{2}',phone_work):
                match = True
            if re.search(r'0\d{2} \d{2} \d{2} \d{2}',phone_work):
                match = True
            if phone_work[:1] == '+' and re.search(r'\d{2} \w+',phone_work[1:]):
                match = True
            if not match:
                warning = phone_work + ' moet 09 999 99 99 of 099 99 99 99 of +99 xxxxxx zijn'
        if not (warning == ''):
            raise osv.except_osv(_('Ongeldig telefoonnummer werk:'), _(warning))
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

    
member_lines()


class member_import(osv.osv_memory):
    _name = 'member.import'
    _description = 'Import Member File'
    _columns = {
        'member_data': fields.binary('Member File', required=True),
        'member_fname': fields.char('Member Filename', size=128, required=True),
    }

    def member_parsing(self, cr, uid, ids, context=None):

        data = self.browse(cr, uid, ids)[0]
        
        memberfile = data.member_data
        memberfilename = data.member_fname

        fys_file_obj = self.pool.get('member.fys.file')
        file_obj = self.pool.get('member.file')
        lines_obj = self.pool.get('member.lines')
        partnerrel_obj = self.pool.get('res.partner.import.rel')
        
        data_md5 = md5(memberfile).digest()       
        exists = fys_file_obj.search(cr, uid, [('filemd5','=',data_md5)], context=context)
        if exists:
            raise osv.except_osv(_('Error'),_('Error') + _('Duplicate Member file'))
        fys_file_id = fys_file_obj.create(cr, uid, {'filemd5': data_md5, 'filename': memberfilename}, context=context)

        recordlist = unicode(base64.decodestring(memberfile), 'windows-1252', 'strict').split('\n')
#         recordlist = unicode(base64.decodestring(memberfile).split('\n'))

        reader = csv.reader(recordlist, delimiter=",", quotechar='"')
        
        file_id = file_obj.create(cr, uid, {'name': memberfilename, 'imported': False}, context=context)

        line = 0
        for row in reader:
            
           line += 1
           
           if row and row[1] != '' and line > 1:
               recruiting_member = row[0]
               last_name = row[1]
               first_name = row[2]
               gender = row[3]
               street = row[4]
               street_nbr = row[5]
               street_bus = row[6]
               zip = row[7]
               city = row[8]
               phone = row[9]
               mobile = row[10]
               birthdate = row[11]
               birthyear = row[12]
               email = row[13]
               phone_work = row[14]
               email_work = row[15]
               street_id = None
               zip_id = None
               country_id = None
               recruiting_member_id = None
               
               to_import = True
               
               city_obj = self.pool.get('res.country.city')
               zipids=city_obj.search(cr, uid, [('zip','=',zip)])
               for recs in city_obj.browse(cr, uid, zipids):
                   zip_id = recs.id
                   country_id = recs.country_id.id
               street_obj = self.pool.get('res.country.city.street')
               streetids=street_obj.search(cr, uid, [('city_id','=',zip_id),('name','=',street)])
               for recs in street_obj.browse(cr, uid, streetids):
                   street_id=recs.id
               if not(street_id):
                   to_import = False
               partner_obj = self.pool.get('res.partner')
               partnerids = partner_obj.search(cr, uid, [('name','=',recruiting_member)])
               if len(partnerids) > 1:
                   to_import = False
               if len(partnerids)==1:
                   for recs in partner_obj.browse(cr, uid, partnerids):
                       recruiting_member_id=recs.id
               if birthdate:
                   birthyear = None
                       
               lineid=lines_obj.create(cr, uid,
                    {
                    'file_id': file_id,
                    'to_import': to_import,
                    'first_name': first_name,
                    'last_name': last_name,
                    'gender': gender,
                    'street': street,
                    'street_id': street_id,
                    'street_nbr': street_nbr,
                    'street_bus': street_bus,
                    'zip': zip,
                    'zip_id': zip_id,
                    'city': city,
                    'country_id': country_id,
                    'email': email,
                    'phone': phone,
                    'mobile': mobile,
                    'email_work': email_work,
                    'phone_work': phone_work,
                    'birthdate': birthdate,
                    'birthyear': birthyear,
                    'recruiting_member': recruiting_member,
                    'recruiting_member_id': recruiting_member_id,
                    'duplicate_ids': None,        
                     }, context=context)

               partnerids = partner_obj.search(cr, uid, 
                        [('zip_id','=',zip_id),('street_id','=',street_id),('street_nbr','=',street_nbr)])
               if partnerids and to_import:
                   lines_obj.write(cr, uid, lineid, {'to_import': False})
               for recs in partner_obj.browse(cr, uid, partnerids):
                   sql='INSERT INTO res_partner_import_rel (import_id, partner_id) VALUES (%d, %d)' % (lineid, recs.id)
                   cr.execute(sql)
                     
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'natuurpunt_imp_members', 'action_member_file')
        action = self.pool.get(model).browse(cr, uid, action_id, context=context)
        return {
            'name': action.name,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'res_model': action.res_model,
#             'domain': action.domain,
#             'context': action.context,
            'type': 'ir.actions.act_window',
#             'search_view_id': action.search_view_id.id,
            'views': [(v.view_id.id, v.view_mode) for v in action.view_ids]
        }


    def rmspaces(s):
        return " ".join(s.split())

member_import()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:# -*- coding: utf-8 -*-

