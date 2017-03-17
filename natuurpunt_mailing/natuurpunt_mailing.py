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

import base64
import ast
import datetime, re, random

from openerp.tools.translate import _
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp

class mailing_category(osv.osv):
    _name = 'mailing.category'
    _description = 'Mailing Category'

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'digital': fields.boolean('Digitaal'),
        'periodical': fields.boolean('Tijdschrift'),
        'payable': fields.boolean('Betalend'),
        'website': fields.boolean('Website'),
        'mailing_subscription_ids': fields.one2many('mailing.subscription', 'category_id', 'Digitale abonnementen'),
                }

mailing_category()

class mailing_group(osv.osv):
    _name = 'mailing.group'
    _description = 'Mailing Group'
    _order = 'seq'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'category_id': fields.many2one('mailing.category', 'Categorie', select=True),
        'payable': fields.boolean('Betalend'),
        'amount': fields.float('Bedrag', digits_compute= dp.get_precision('Product Price')),
        'product_ids': fields.many2many('product.product', 'product_mailing_group_rel', 'mailing_group_id', 'product_id', 'Producten'),
        'export_details': fields.boolean('Export details'),
        'export_partner': fields.boolean('Export partner'),
        'filter_ids': fields.many2many('ir.filters', 'mailing_group_filter_rel', 'mailing_group_id', 'filter_id', 'Filters'),
        'seq': fields.integer('Sequentie'),
                }
 
mailing_group()
 
class mailing_mailing(osv.osv):
    _name = 'mailing.mailing'
    _description = 'Mailing'
    _order = 'date_ship desc'
 
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'category_id': fields.many2one('mailing.category', 'Categorie', select=True),
        'date_ship': fields.date('Editiedatum', required=True, select=True),
        'list_ids': fields.one2many('mailing.list', 'mailing_id', 'Mailing Lijsten'),
        'digital': fields.related('category_id', 'digital', type='boolean', string="Digitaal"),
        'website': fields.boolean('Website'),
        'description': fields.text('Omschrijving'),
                }
 
mailing_mailing()
 
class mailing_list(osv.osv):
    _name = 'mailing.list'
    _description = 'Mailing List'
    _rec_name = 'mailing_name'
    _order = 'id desc'

    _columns = {
		'mailing_id': fields.many2one('mailing.mailing', 'Mailing', select=True),
        'mailing_name': fields.related('mailing_id', 'name', type='char', string="Name"),
		'group_id': fields.many2one('mailing.group', 'Mailing Groep', select=True),
		'closed': fields.boolean('Afgesloten'),
        'list_partner_ids': fields.one2many('mailing.list.partner', 'list_id', 'Mailing List Partners'),
        'generate_reference': fields.boolean('Communication'),
        'generate_lidkaart': fields.boolean('Lidkaart'),
        'generate_welkomstpakket': fields.boolean('Welkomstpakket'),
        'exported': fields.boolean('File aangemaakt'),
        'processed': fields.boolean('Verwerkt'),
        'mailing_date': fields.date('Verzenddatum', required=True),
                }

    def create(self, cr, uid, vals, context=None):
        res = super(mailing_list, self).create(cr, uid, vals, context=context)
        ml = self.browse(cr, uid, res)
        partner_obj = self.pool.get('res.partner')
        mailing_list_partner_obj = self.pool.get('mailing.list.partner')
        seq = ml.group_id.seq
        reference = ''
        if ml.generate_reference:
            reference = 'yes'

        for mgf in ml.group_id.filter_ids:
            dom = ast.literal_eval(mgf.domain)
            partner_ids = partner_obj.search(cr, uid, dom, context=context)
            for line in partner_obj.browse(cr, uid, partner_ids, context=context):
                exists = mailing_list_partner_obj.search(cr, uid, [('partner_id','=',line.id), ('mailing_id','=',ml.mailing_id.id)], context=context)
                if exists:
                    record = mailing_list_partner_obj.browse(cr, uid, exists[0])
                    if seq < record.seq:
                        mailing_list_partner_obj.write(cr, uid, exists[0], {'seq':seq})
                else:
                    mailing_list_partner_obj.create(cr, uid, {
                        'partner_id': line.id,
                        'partner_name': line.name,
                        'list_id': ml.id,
                        'reference': reference,
                        'mailing_id': ml.mailing_id.id,
                        'mailing_date': ml.mailing_date,
                        'seq': ml.group_id.seq
                    }, context=context)
            
        return res
 
    def process_mailing_list(self, cr, uid, vals, context=None):
        print 'vals:', vals
        mailing_list_obj = self.pool.get('mailing.list')
        partner_obj = self.pool.get('res.partner')
        ml = mailing_list_obj.browse(cr, uid, vals[0])
        if ml.generate_lidkaart or ml.generate_welkomstpakket:
            for mlp in ml.list_partner_ids:
                partner = partner_obj.browse(cr, uid, mlp.partner_id.id)
                if ml.generate_lidkaart:
                     partner_obj.write(cr, uid, [mlp.partner_id.id], {'lidkaart':True, 'date_lidkaart':ml.mailing_date,})
                if ml.generate_welkomstpakket:
                     partner_obj.write(cr, uid, [mlp.partner_id.id], {'welkomstpakket':True, 'date_welkomstpakket':ml.mailing_date,})
        mailing_list_obj.write(cr, uid, vals[0], {'processed':True})
        return True


mailing_list()

class mailing_list_partner(osv.osv):
    _name = 'mailing.list.partner'
    _description = 'Mailing List/Partner'
    _rec_name = 'mailing_name'
    _order= 'partner_name, id desc'
      
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', select=1, ondelete='restrict'),
        'partner_name': fields.char('Name', size=128),
        'list_id': fields.many2one('mailing.list', 'Lijst', select=False),
        'reference': fields.char('Communication', size=64, select=1),
        'mailing_id': fields.many2one('mailing.mailing', 'Mailing', select=1),
        'mailing_name': fields.related('mailing_id', 'name', type='char', string="Mailing"),
        'mailing_date': fields.date('Verzenddatum', required=True),
        'seq': fields.integer('Sequentie'),
        'return_reason_id': fields.many2one('mailing.return.reason', 'Retour', select=False),
                }

    def create(self, cr, uid, vals, context=None):
# enkel te doen als de .mailing_id.generate_reference = True
        if vals['reference'] == 'yes':       
            reference = self.generate_bbacomm(cr, uid, 'yes', vals['partner_id'])
            vals['reference'] = reference['value']['reference']
        return super(mailing_list_partner, self).create(cr, uid, vals, context=context)

    def check_bbacomm(self, val):
        supported_chars = '0-9+*/ '
        pattern = re.compile('[^' + supported_chars + ']')
        if pattern.findall(val or ''):
            return False
        bbacomm = re.sub('\D', '', val or '')
        if len(bbacomm) == 12:
            base = int(bbacomm[:10])
            mod = base % 97 or 97
            if mod == int(bbacomm[-2:]):
                return True
        return False

    def generate_bbacomm(self, cr, uid, reference, partner_id, context=None):
        prev_seq = 0
        while reference == 'yes' or self.check_bbacomm_exists(cr, uid, reference):
            partner_ref = str(partner_id)
            partner_ref_nr = re.sub('\D', '', partner_ref or '')
            if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
                partner_ref_nr = "%s%s" % ('99999', partner_ref_nr.ljust(2, '0'))
            else:
                partner_ref_nr = partner_ref_nr.ljust(7, '0')
            prev_seq += 1
            if prev_seq < 999:
                seq = '%03d' % (prev_seq)
            else:
                raise osv.except_osv(_('Warning!'),
                    _('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!' \
                      '\nPlease create manually a unique BBA Structured Communication.'))
            bbacomm = partner_ref_nr + seq
            base = int(bbacomm)
            mod = base % 97 or 97
            reference = '+++%s/%s/%s%02d+++' % (partner_ref_nr[:3], partner_ref_nr[3:], seq, mod)
        return {'value': {'reference': reference}}

    def check_bbacomm_exists(self, cr, uid, val):
        same_refs = self.search(cr, uid,
            [('reference', '=', val)])
        if same_refs:
            print 'dubbele bba in mailing: ', val
            return True
        obj_account_invoice = self.pool.get('account.invoice')
        same_inv_refs = obj_account_invoice.search(cr, uid, [('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                         ('reference', '=', val)])
        if same_inv_refs:
            print 'dubbele bba in invoice: ', val
            return True
        return False
  
mailing_list_partner()

class mailing_end_reason(osv.osv):
    _name = 'mailing.end.reason'
    _description = 'Mailing End Reasons'

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'description': fields.char('Description', size=64, required=True, translate=True),
                }

mailing_end_reason()

class mailing_return_reason(osv.osv):
    _name = 'mailing.return.reason'
    _description = 'Mailing Return Reasons'

    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'description': fields.char('Description', size=64, required=True, translate=True),
                }

mailing_return_reason()

class mailing_subscription(osv.osv):
    _name = 'mailing.subscription'
    _description = 'Mailing Abonnement'

    _columns = {
        'category_id': fields.many2one('mailing.category', 'Abonnement', select=True),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True, ondelete='restrict'),
        'date_start': fields.date('Startdatum', required=True),
        'date_stop': fields.date('Einddatum', required=False),
        'end_reason_id': fields.many2one('mailing.end.reason', 'Reden Stopzetting'),
                }

mailing_end_reason()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    _columns = {
        'mailing_list_partner_ids': fields.one2many('mailing.list.partner', 'partner_id', 'Mailing Lijsten'),
        'mailing_subscription_ids': fields.one2many('mailing.subscription', 'partner_id', 'Digitale abonnementen'),
        'iets_te_verbergen': fields.boolean('Iets te verbergen', required=False),
        'welkomstpakket': fields.boolean('Welkomstpakket'),
        'date_welkomstpakket': fields.date('Datum welkomstpakket', required=False),
        'lidkaart': fields.boolean('Lidkaart'),
        'date_lidkaart': fields.date('Datum lidkaart', required=False),
        'periodical_1_id': fields.many2one('mailing.mailing', 'Tijdschrift 1'),
        'periodical_2_id': fields.many2one('mailing.mailing', 'Tijdschrift 2'),
    }

res_partner() 

class export_mailing_list(osv.osv_memory):
    """ Export mailing lijst """
    _name = "export.mailing.list"
    _description = "Export mailing lijst"

    def _get_file_name(self, cr, uid, context=None):
        if context.get('active_id', False):
            return 'maillist.txt'
        return ''
    
    def _get_file_data(self, cr, uid, context=None):
        if context.get('file_save', False):
            return base64.encodestring(context['file_save'].encode('utf8'))
        return ''
    
    _columns = {
        'file_name': fields.char('File Name', size=32),
        'msg': fields.text('File created', size=64, readonly=True),
        'file_save': fields.binary('Save File'),
    }

    _defaults = {
        'msg': 'Save the File.',
        'file_save': _get_file_data,
        'file_name': _get_file_name,
    }
    
    def create_file(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        if context['active_model'] == 'mailing.list':
            obj_mailing_list = self.pool.get('mailing.list')
            ml = obj_mailing_list.browse(cr, uid, context['active_id'])
#   op het mailinglistscherm kun je de export doen voor een niet-digitale lijst (voor één bepaalde lijst)
            if ml.mailing_id.category_id.digital:
                return False
            else:
                data_of_file = '"DBId"|"Naam"|"Voornaam"|"Familienaam"|"Adres"|"Zip"|"City"|"Country"|"Lidnummer"'
                betaling = False
                communication = False
                bedrag = 0
                partner = False
                detail = False
                products = {}
                if ml.group_id.payable:
                    betaling = True
                    bedrag += ml.group_id.amount
                if ml.generate_reference:
                    communication = True
                if ml.group_id.export_partner:
                    partner = True
                if ml.group_id.export_details:
                    detail = True
                for p in ml.group_id.product_ids:
                    if p.name not in products:
                        products[p.name] = [p.name]
                for i, j in products.iteritems():
                    data_of_file += ',"'
                    data_of_file += j[0]
                    data_of_file += '"'
                if detail:
                    data_of_file += '|"Telefoon"|"Telefoon werk"|"Mobile"|"Email"|"Email werk"|"Geboortedatum"'
                if partner:
                    data_of_file += '|"Naam partner"'
                if communication:
                    data_of_file += '|"Structured Communication"'
                if betaling:
                    data_of_file += '|"Bedrag"'
                for mlp in ml.list_partner_ids:
                    lines_data = {
                                  'DBId': str(mlp.partner_id.id),
                                  'Naam': mlp.partner_id.name,
                                  'Voornaam': mlp.partner_id.first_name,
                                  'Familienaam': mlp.partner_id.last_name,
                                  'Adres': mlp.partner_id.street,
                                  'Zip': mlp.partner_id.zip,
                                  'City': mlp.partner_id.city,
                                  'Country': mlp.partner_id.country_id.name,
                                  'Lidnr': mlp.partner_id.membership_nbr,
                                  'Telefoon': mlp.partner_id.phone,
                                  'Telefoon werk': mlp.partner_id.phone_work,
                                  'Mobile': mlp.partner_id.mobile,
                                  'Email': mlp.partner_id.email,
                                  'Email werk': mlp.partner_id.email_work,
                                  'Geboortedatum': mlp.partner_id.birthday,
                                  'Naam partner': mlp.partner_id.relation_partner_id.name or "",
                                  'Structured Communication': mlp.reference,
                                  'Bedrag': str(bedrag),
                                 }
                    data_of_file += '\n"%(DBId)s"|"%(Naam)s"|"%(Voornaam)s"|"%(Familienaam)s"|"%(Adres)s"|"%(Zip)s"|"%(City)s"|"%(Country)s"|"%(Lidnr)s"' % (lines_data)
                    for prod in products.iteritems():
                        data_of_file += '|"true"'
                    if detail:
                        data_of_file += '|"%(Telefoon)s"|"%(Telefoon werk)s"|"%(Mobile)s"|"%(Email)s"|"%(Email werk)s"|"%(Geboortedatum)s"' % (lines_data)
                    if partner:
                        data_of_file += '|"%(Naam partner)s"' % (lines_data)
                    if communication:
                        data_of_file += '|"%(Structured Communication)s"' % (lines_data)
                    if betaling:
                        data_of_file += '|%(Bedrag)s' % (lines_data)
                obj_mailing_list.write(cr, uid, ml.id, {'exported':True})
        else:
            obj_mailing = self.pool.get('mailing.mailing')
            mm = obj_mailing.browse(cr, uid, context['active_id'])
#   op het mailingscherm kun je de export doen voor een digitale mailing            
            if not(mm.category_id.digital):
                return False
            else:
                data_of_file = '"DBId"|"Naam"|"Voornaam"|"Familienaam"|"Email"|"Lidnummer"'
                for ms in mm.category_id.mailing_subscription_ids:
                    if not(ms.date_stop) or datetime.datetime.strptime(ms.date_stop,'%Y-%m-%d') > datetime.datetime.strptime(mm.date_ship,'%Y-%m-%d'):
                        if ms.partner_id.email:
                            lines_data = {
                                          'DBId': str(mlp.partner_id.id),
                                          'Naam': ms.partner_id.name,
                                          'Voornaam': ms.partner_id.first_name,
                                          'Familienaam': ms.partner_id.last_name,
                                          'Email': ms.partner_id.email,
                                          'Lidnr': ms.partner_id.membership_nbr,
                                          }
                            data_of_file += '\n"%(DBId)s"|"%(Naam)s"|"%(Voornaam)s"|"%(Familienaam)s"|"%(Email)s"|"%(Lidnr)s"' % (lines_data)
        model_data_ids = mod_obj.search(cr, uid, [['model', '=', 'ir.ui.view'], ['name', '=', 'view_mailing_list_save']], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        data_of_file = data_of_file.replace('"False"', '""')
        context['file_save'] = data_of_file
        return {
            'name': _('Save mailing list file'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'export.mailing.list',
            'views': [(resource_id, 'form')],
            'view_id': 'view_mailing_list_save',
            'type': 'ir.actions.act_window',
             'target': 'new',
        }

export_mailing_list()

class mailing_list_import_partners(osv.osv_memory):

    _name = "mailing.list.import.partners"
    _description = "Import partners on mailing list"
    _columns = {
        'partner_ids': fields.many2many('res.partner', 'mailing_list_partner_relation', 'mailing_list_id', 'partner_id', 'Partners'),
    }

    def populate_mailing_list(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailing_list_id = context.get('mailing_list_id', False)
        if not mailing_list_id:
            return {'type': 'ir.actions.act_window_close'}
       
        data =  self.read(cr, uid, ids, context=context)[0]
        partner_ids = data['partner_ids']
        if not partner_ids:
            return {'type': 'ir.actions.act_window_close'}

        partner_obj = self.pool.get('res.partner')
        mailing_list_obj = self.pool.get('mailing.list')
        mailing_list_partner_obj = self.pool.get('mailing.list.partner')
        mailing_list = mailing_list_obj.browse(cr, uid, mailing_list_id, context=context)
        seq = mailing_list.group_id.seq
        reference = ''
        if mailing_list.generate_reference:
            reference = 'yes'

        for line in partner_obj.browse(cr, uid, partner_ids, context=context):
            exists = mailing_list_partner_obj.search(cr, uid, [('partner_id','=',line.id), ('mailing_id','=',mailing_list.mailing_id.id)], context=context)
            if exists:
                record = mailing_list_partner_obj.browse(cr, uid, exists[0])
                if seq < record.seq:
                    mailing_list_partner_obj.write(cr, uid, exists[0], {'seq':seq})
            else:
### Test op out_out of opt_out_letter, of dit doen via filter?
                mailing_list_partner_obj.create(cr, uid, {
                    'partner_id': line.id,
                    'partner_name': line.name,
                    'list_id': mailing_list.id,
                    'reference': reference,
                    'mailing_id': mailing_list.mailing_id.id,
                    'mailing_date': mailing_list.mailing_date,
                    'seq': seq,
                }, context=context)
        return {'type': 'ir.actions.act_window_close'}

mailing_list_import_partners()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
