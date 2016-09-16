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
from openerp import SUPERUSER_ID
import datetime
from mx import DateTime
import time
from openerp.tools.translate import _
import urllib2
import xml.etree.ElementTree as ET
import re
import logging
from natuurpunt_tools import difflib_cmp, AttrDict, compose
from natuurpunt_tools import uids_in_group
from functools import partial

_logger = logging.getLogger('natuurpunt_web_membership')

class OrganisatiePartnerEnum():
    AFDELING = 1
    RESERVAAT = 2
    KERN = 3
    WERKGROEP = 5
    REGIONALE = 7
    BEZOEKERSCENTRUM = 10

def get_match_vals(vals):
    """
    subset of fields needed to match
    """
    match_fields = ['first_name','last_name']
    ref = AttrDict()
    [setattr(ref,k,v) for k,v in vals.iteritems() if k in match_fields]
    return ref

def match_with_existing_partner(obj,cr,uid,vals):
    """
    when we could not find a partner by its unique identifier = email
    we do an extra check if we can find it based on address and name
    """
    def match_on_fullname(target_ids):
        match_str = lambda p: "{0}_{1}".format(p.first_name, p.last_name)
        match_target_list = []
        for partner in obj.browse(cr,uid,target_ids):
            match_target_list.append((partner.id, match_str(partner)))
        return difflib_cmp(match_str(ref_vals), match_target_list)[0] if match_target_list else False

    def match_names_seperatly(cmp_res):
        if cmp_res and cmp_res[1] > 0.5:
            partner = obj.browse(cr,uid,cmp_res[0])
            cmp_res_first_name = difflib_cmp(ref_vals.first_name, [(partner.id, partner.first_name)])[0]
            cmp_res_last_name = difflib_cmp(ref_vals.last_name, [(partner.id, partner.last_name)])[0]
            return partner if cmp_res_first_name[1] >= 0.7 and cmp_res_last_name[1] >= 0.85 else False
        else:
            return False

    ref_vals = get_match_vals(vals)
    if vals['street_id']:
       target_domain = [
            ('street_id','=',vals['street_id']),
            ('zip_id','=',vals['zip_id']),
            ('street_nbr','=',vals['street_nbr']),
       ]
    else:
       target_domain = [
            ('street','=',vals['street']),
            ('zip','=',vals['zip']),
            ('street_nbr','=',vals['street_nbr']),
       ]
    partner = compose(
                match_on_fullname,
                match_names_seperatly,
                lambda p: p if p and p.membership_state in ['old','none'] else False,
                lambda p: p if p and not(p.donation_line_ids) else False
              )(obj.search(cr,uid,target_domain))
    return partner if partner else False

def partner_url(obj, cr):
    link = "<b><a href='{}?db={}#id={}&view_type=form&model=res.partner'>{}</a></b>"
    base_url = obj.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
    return link, base_url

def alert_when_customer_or_supplier(obj,cr,uid,partner):
    """
    when partner is known as customer or supplier
    raise an exception so we can inform website API that we can't
    use this partner for memberships without manual interaction
    """
    # TODO
    if partner and (partner.customer or partner.supplier):
        link, base_url = partner_url(obj, cr)
        alert = 'Lidmaatschap aanvraag van contact met klant/lev. status'
        body = link.format(base_url,cr.dbname,partner.id,partner.name + ' : ' + alert)
        mail_group_id = obj.pool.get('mail.group').group_word_lid_alerts(cr,uid)
        message_id = obj.pool.get('mail.group').message_post(cr, uid, mail_group_id,
                                body=body,
                                subtype='mail.mt_comment', context={})
        obj.pool.get('mail.message').set_message_read(cr, uid, [message_id], False)
        website_alert = """ Er is een probleem opgedoken bij de aanmaak van je lidmaatschap.
                            We nemen zo snel mogelijk contact op.
                            Heb je vragen? Stuur een e-mail bericht naar ledenservice@natuurpunt.be"""
        return partner, website_alert
    else:
        return partner, False

def alert_when_name_matched_existing_partner(obj,cr,uid,partner):
    """
    when partner was matched on name... send an alert to crm team 
    """
    if partner:
        link, base_url = partner_url(obj, cr)
        alert = 'Lidmaatschap aanvraag naam match'
        body = link.format(base_url,cr.dbname,partner.id,partner.name + ' : ' + alert)
        mail_group_id = obj.pool.get('mail.group').group_word_lid_alerts(cr,uid)
        message_id = obj.pool.get('mail.group').message_post(cr, uid, mail_group_id,
                                body=body,
                                subtype='mail.mt_comment', context={})
        obj.pool.get('mail.message').set_message_read(cr, uid, [message_id], False)
    return partner

class mail_group(osv.osv):
    _inherit = 'mail.group'

    def group_word_lid_alerts(self, cr, uid, context=None):
        vals = {'name':'website meldingen'}
        mail_group_id = self.search(cr, uid, [('name','=',vals['name'])])
        if mail_group_id:
            return mail_group_id
        else:
            # first automatic creation of discussion group
            # or when group is removed
            mail_alias = self.pool.get('mail.alias')
            if not vals.get('alias_id'):
                vals.pop('alias_name', None)  # prevent errors during copy()
                alias_id = mail_alias.create_unique_alias(cr, uid,
                              # Using '+' allows using subaddressing for those who don't
                              # have a catchall domain setup.
                              {'alias_name': "group+" + vals['name']},
                              model_name=self._name, context=context)
                vals['alias_id'] = alias_id

            # get parent menu
            menu_parent = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'membership', 'menu_membership')
            menu_parent = menu_parent and menu_parent[1] or False

            # Create menu id
            mobj = self.pool.get('ir.ui.menu')
            menu_id = mobj.create(cr, SUPERUSER_ID, {'name': vals['name'], 'parent_id': menu_parent}, context=context)
            vals['menu_id'] = menu_id

            # Create group and alias
            mail_group_id = super(mail_group, self).create(cr, uid, vals, context=context)
            mail_alias.write(cr, uid, [vals['alias_id']], {"alias_force_thread_id": mail_group_id}, context)
            group = self.browse(cr, uid, mail_group_id, context=context)

            # Create client action for this group and link the menu to it
            ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'action_mail_group_feeds')
            if ref:
                search_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'view_message_search')
                params = {
                    'search_view_id': search_ref and search_ref[1] or False,
                    'domain': [
                        ('model', '=', 'mail.group'),
                        ('res_id', '=', mail_group_id),
                    ],
                    'context': {
                        'default_model': 'mail.group',
                        'default_res_id': mail_group_id,
                    },
                    'res_model': 'mail.message',
                    'thread_level': 1,
                    'header_description': self._generate_header_description(cr, uid, group, context=context),
                    'view_mailbox': True,
                    'compose_placeholder': 'Send a message to the group',
                }
                cobj = self.pool.get('ir.actions.client')
                newref = cobj.copy(cr, SUPERUSER_ID, ref[1], default={'params': str(params), 'name': vals['name']}, context=context)
                mobj.write(cr, SUPERUSER_ID, menu_id, {'action': 'ir.actions.client,' + str(newref), 'mail_group_id': mail_group_id}, context=context)

            crm_users = uids_in_group(self, cr, uid, 'group_natuurpunt_crm_manager', partner=True, context=context)
            self.message_subscribe(cr, uid, [mail_group_id], crm_users, context=context)
            return [mail_group_id]

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _web_membership_product(self,cr,uid,subscriptions,context=None):        
        # search membership products
        current_date = DateTime.now().strftime('%Y-%m-%d')
        sql_stat = "select id from product_product where membership_product and membership_date_from <= '{0}' and membership_date_to >= '{0}'".format(current_date)
        cr.execute(sql_stat)
        mem_prod_ids = map(lambda x: x[0], cr.fetchall())
        # membership defaulf product
        mem_prod = 'Gewoon lid'
                
        # website membership product = membership default + subscriptions
        web_prod_list = [mem_prod]
        web_prod_list.extend([s['name'] for s in subscriptions])
        res = self.subscriptions_to_membership_product(cr,uid,mem_prod_ids,web_prod_list,context=context)
        
        # default fall back is 'gewoon lid'
        # better a product to sell than nothing        
        if not res:
            res = self.subscriptions_to_membership_product(cr,uid,mem_prod_ids,[mem_prod],context=context)

        return res
    
    def subscriptions_to_membership_product(self,cr,uid,ids,web_prod_list,context=None):
        product_obj = self.pool.get('product.product')
        for product in product_obj.browse(cr, uid, ids, context=context):
            # membership product = membership default + included products
            mem_prod_list = web_prod_list[:1]
            if product.included_product_ids:
                 for included_product in product_obj.browse(cr, uid, product.included_product_ids, context=context):
                    prod_name = included_product.id.name_template
                    if mem_prod_list[0] != prod_name:
                        mem_prod_list.append(prod_name)
            # intersection match then return product_id
            if set(mem_prod_list) == set(web_prod_list):
               return product.id
        return None
    
    def membership_renewal_product_to_subscriptions(self,cr,uid,ids,context=None):    
        for partner in self.browse(cr, uid, ids, context=context):
            if partner.membership_renewal_product_id:
                mem_prod_list = []
                mem_prod = 'Gewoon lid'
                product_obj = self.pool.get('product.product')
                product = product_obj.browse(cr, uid, partner.membership_renewal_product_id.id, context=context)
                for included_product in product_obj.browse(cr, uid, product.included_product_ids, context=context):
                    prod_name = included_product.id.name_template
                    if mem_prod != prod_name:
                        mem_prod_list.append(prod_name)
                # convert list of subscriptions to list {'name':subscription}                                
                return map(lambda v: {'name':v},mem_prod_list)
        return None

    def address_origin_website(self,cr,uid,context=None):
        address_origin_obj = self.pool.get('res.partner.address.origin')
        ids = address_origin_obj.search(cr, uid, [('ref','=','website')],context=context)
        if ids:
            return ids[0]
        else:
            return False

    def _verify_membership_origin(self,cr,uid,ids,context=None):
        membership_origin_obj = self.pool.get('res.partner.membership.origin')
        if membership_origin_obj.search(cr, uid, [('id','in',ids)],context=context):
            return True
        else:
            return False

    def _verify_recruiting_organisation(self,cr,uid,ids,context=None):
        recruiting_organisation_obj = self.pool.get('res.partner')
        org_ids = [
            OrganisatiePartnerEnum.AFDELING,
            OrganisatiePartnerEnum.WERKGROEP,
            OrganisatiePartnerEnum.REGIONALE,
            OrganisatiePartnerEnum.BEZOEKERSCENTRUM,
        ]
        if recruiting_organisation_obj.search(cr, uid, [('id','in',ids),('organisation_type_id','in',org_ids)],context=context):
            return True
        else:
            return False

    def partner_state_website_double_address(self,cr,uid,context=None):
        partner_state_obj = self.pool.get('res.partner.state')
        ids = partner_state_obj.search(cr, uid, [('ref','=','1')],context=context)
        if ids:
            return ids[0]
        else:
            return False

    def _web_membership_partner(self,cr,uid,ids,vals,context=None):
        if ids:
            # address update via website resets status
            vals['address_state_id'] = False
            self.write(cr,uid,ids,vals,context=context)
        else:
            # address via website
            vals['address_origin_id'] = self.address_origin_website(cr,uid,context=context)
            ids.append(self.create(cr,uid,vals,context=context))
        return ids

    def _bban2bic(self,bank_account_number=None):
        """webservice BIC"""
        try:
            base_url = 'http://www.ibanbic.be/IBANBIC.asmx/BBANtoBIC?Value'
            url = '%s=%s' % (base_url, bank_account_number.replace(' ', ''))
            response = urllib2.urlopen(url).read()
            root = ET.fromstring(response)
            bic = root.text.replace(' ', '')
        except Exception:
            bic = 'DUMMY'    
        return bic

    def _get_bic_id(self,cr,uid,bic):
        sql_stat = "select id from res_bank where name = '{0}'".format(bic)
        cr.execute(sql_stat)
        ids = map(lambda x: x[0], cr.fetchall())
        return ids[0] if ids else None

    def create_web_membership_mandate_invoice(self,cr,uid,ids,selected_product_id=None,datas=None,context=None):

        bank_acc = datas['bank_account_number'] 
        
        bic_id = self._get_bic_id(cr,uid,self._bban2bic(bank_acc))
        bic_id = bic_id if bic_id else self._get_bic_id(cr,uid,'DUMMY')

        scan_binary = datas['scan']

        mandate_obj = self.pool.get('partner.create.bank.mandate.invoice')
        vals = {'partner_id':ids[0],
                'bic_id':bic_id,
                'bank_account':bank_acc,
                'signature_date':time.strftime('%Y-%m-%d %H:%M:%S'),
                'membership_product_id':selected_product_id,
                'scan':scan_binary,}
        # create os_memory object 
        mandate_id = mandate_obj.create(cr,uid,vals)
        mandate = mandate_obj.browse(cr,uid,mandate_id)
        res = mandate.create_bank_mandate_invoice(context=context)
        # return invoice via context in variable web_invoice_id
        if 'context' in res:
            if 'web_invoice_id' in res['context']:
                return [res['context']['web_invoice_id']]
            else:
                return 0
        else:
            return 0

    def create_web_membership(self,cr,uid,ids,vals,datas,context=None):
        context = context or {}
        if ids == None:
            ids = []

        # membership_origin_id                    
        membership_origin_id = datas.get('membership_origin_id', 0)
        if self._verify_membership_origin(cr,uid,[membership_origin_id],context=context):
            vals['membership_origin_id'] = membership_origin_id

        # recruiting_organisation_id
        recruiting_organisation_id = datas.get('recruiting_organisation_id', 0)
        if not(self._verify_recruiting_organisation(cr,uid,[recruiting_organisation_id],context=context)):
            datas.pop('recruiting_organisation_id', None)

        # convert website membership + subscriptions to product
        product_id = self._web_membership_product(cr,uid,datas['subscriptions'],context=context)

        # renewal product...? , update contact  
        if datas.get('membership_renewal', False):
            vals['membership_renewal_product_id'] = product_id

        # override default from website            
        vals['customer'] = False

        # membership partner update or create
        _logger.info(vals)
        _logger.info("partner ids:{}".format(ids))
        if not ids:
            ids,website_alert = compose(
                    partial(match_with_existing_partner,self,cr,uid),
                    partial(alert_when_name_matched_existing_partner,self,cr,uid),
                    partial(alert_when_customer_or_supplier,self,cr,uid),
                    lambda (p,a):([p.id],a) if p else (ids,a)
            )(vals)
            _logger.info("partner match ids:{}".format(ids))
        else:
            ids,website_alert = compose(
                    lambda ids: self.browse(cr,uid,ids[0],context=context),
                    partial(alert_when_customer_or_supplier,self,cr,uid),
                    lambda (p,a):([p.id],a)
            )(ids)            

        if website_alert:
            _logger.info("website alert:{}".format(website_alert))
            return {'id':0,'alert_message':website_alert}
        else:
            ids = self._web_membership_partner(cr,uid,ids,vals,context=context)

        methods = {'OGONE':self.create_membership_invoice,
                   'SEPA':self.create_web_membership_mandate_invoice,
                   'OFFLINE':self.create_membership_invoice,}
        method = datas['method'].upper() if 'method' in datas else None
        if method in methods:
            inv_ids = methods[method](cr,uid,ids,selected_product_id=product_id,datas=datas,context=context)
        else:
            inv_ids = 0

        if inv_ids:
            invoice_obj = self.pool.get('account.invoice')
            for invoice in invoice_obj.browse(cr,uid,inv_ids,context=context):
                return {'id':invoice.partner_id.id,'invoice_id':invoice.id,'reference':invoice.reference}
        else:
            return {'id':ids[0]}

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
