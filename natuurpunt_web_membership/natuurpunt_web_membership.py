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
import datetime
from mx import DateTime
import time
from openerp.tools.translate import _
import urllib2
import xml.etree.ElementTree as ET
import re
import logging

_logger = logging.getLogger('natuurpunt_web_membership')

class OrganisatiePartnerEnum():
    AFDELING = 1
    RESERVAAT = 2
    KERN = 3
    WERKGROEP = 5
    REGIONALE = 7
    BEZOEKERSCENTRUM = 10

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

    def partner_match_in_onchange_street_warning(self,cr,uid,name,onchange_street_res,context=None):
        #http://stackoverflow.com/questions/3429086/python-regex-to-get-all-text-until-a-and-get-text-inside-brackets        
        #{'message': u'De volgende contacten zijn reeds geregistreerd op dit adres: Truus Van Kelst (131822) \n', 'title': u'Waarschuwing!'}
        if 'warning' in onchange_street_res:
            warning = onchange_street_res['warning']
            # split string on first occurrence ':'
            regex = re.compile("(.*?:)")
            regex_match = regex.match(warning['message'])
            if regex_match:
                # process string after ':' by slicing on length
                double_address_list = warning['message'][len(regex_match.group(0)):].strip().split('\n')
                regex = re.compile("(.*?\s)*")
                for w in double_address_list:
                    regex_match = regex.match(w.strip())
                    if regex_match and name.strip().upper() == regex_match.group(0).strip().upper():
                        return True
                            # if name match return id between (123)
                            # reverse string and regex match on )321(
                            # return reverse string 123                     
                            #regex_id = re.compile("\)(.*?)\(")
                            #regex_match = regex_id.match(w[::-1].strip())
                            #if regex_match:
                            #    return [long(regex_match.group(1)[::-1])]
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
        _logger.info(ids)
        _logger.info(vals)
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
