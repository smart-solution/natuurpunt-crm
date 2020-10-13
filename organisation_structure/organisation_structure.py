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

class res_organisation_type(osv.osv):
	_name = 'res.organisation.type'
	
	_columns = {
		'name': fields.char('Organisatietype', size=128, required=True),
		'function_type_ids': fields.many2many('res.function.type', 'res_organisation_type_function_rel', 'organisation_type_id', 'function_type_id', 'Functietypes'),
                'function_dependency_ids': fields.one2many('res.function.dependency', 'organisation_type_id', 'Function dependency'),
		'analytic_account_required': fields.boolean('Analytische code verplicht'),
		'unique_type': fields.boolean('Uniek'),
		'organisation': fields.boolean('Organisatie'),
		'remittance': fields.boolean('Afdracht'),
		#'radius_of_action': fields.boolean('Werkingsveld'),
		'organisation_relation_ids': fields.many2many('res.organisation.relation', 'res_organisation_type_relation_rel', 'organisation_type_id', 'relation_type_id', 'Organisatierelaties'),
		'nature_area': fields.boolean('Natuurgebied'),
		'display_functions_company': fields.boolean('Toon functies vzw'),
		'display_functions_person': fields.boolean('Toon functies persoon'),
		'display_remittance': fields.boolean('Toon afdracht'),
		'display_relations': fields.boolean('Toon relaties-tab'),
		'display_relations_vertical': fields.boolean('Toon verticale relaties'),
		'display_relations_horizontal': fields.boolean('Toon horizontale relaties'),
		#'display_radius_action': fields.boolean('Toon werkingsveld'),
		'display_niche': fields.boolean('Toon niche'),
		#'display_niche_category': fields.boolean('Toon niche categorie'),
		'display_reference': fields.boolean('Toon referentie'),
		'display_npca': fields.boolean('Toon NPCA'),
		'display_regional_level': fields.boolean('Toon regionaal niveau'),
		'display_nature_up': fields.boolean('Toon bovenliggend natuurgebied'),
		'display_partner_up': fields.boolean('Toon bovenliggende relatie'),
		'display_regional_definition': fields.boolean('Toon regionale definitie'),
		'display_regional_definition_m2m': fields.boolean('Toon regionale definitie (m2m)'),
		'display_analytic': fields.boolean('Toon analytische code'),
		'display_address': fields.boolean('Toon adres'),
		'display_regional_partnership': fields.boolean('Toon regionaal samenwerkingsverband'),
		'display_contacts': fields.boolean('Toon contacten'),
		'display_ownership': fields.boolean('Toon eigendomssituatie en toegankelijkheid'),
		'display_invoicing': fields.boolean('Toon Boekhouding'),
		'display_insurance': fields.boolean('Toon verzekeringen'),
		'display_suppliers': fields.boolean('Toon nutsleveranciers'),
		'display_extra_info': fields.boolean('Toon bijkomende info'),
		'display_building_function': fields.boolean('Toon functie gebouw'),
		'display_building_capakey': fields.boolean('Toon capakey gebouw'),
		'display_building_date_end': fields.boolean('Toon einddatum gebouw'),
        'display_phone': fields.boolean('Toon telefoonnummer'),
	}

res_organisation_type()

class res_function_dependency(osv.osv):
        _name = 'res.function.dependency'

        _columns = {
            'organisation_type_id': fields.many2one('res.organisation.type', 'Organisation type', required=True, ondelete='cascade', select=True, readonly=True),
            'function_type_id': fields.many2one('res.function.type', 'function', select=True),
            'depends_on_function_type_id': fields.many2one('res.function.type', 'depends on function', select=True),
            'categ_id': fields.many2one('res.niche.categ', 'Nichecategorie', select=True),
            'regional_level': fields.selection([('L','Lokaal'),('G','Gewestelijk'),('R','Regionaal'),('P','Provinciaal')], string='Regionaal niveau', size=1),
            'occurance': fields.integer('occurance',),
        }

res_function_dependency()

class res_function_categ(osv.osv):
	_name = 'res.function.categ'
	
	_columns = {
		'name': fields.char('Functiecategorie', size=128, required=True),
	}

res_function_categ()

class res_function_type(osv.osv):
	_name = 'res.function.type'
	
	_columns = {
		'name': fields.char('Functietype', size=128, required=True),
		'organisation_type_ids': fields.many2many('res.organisation.type', 'res_organisation_type_function_rel', 'function_type_id', 'organisation_type_id', 'Organisatietypes'),
		'unique_type': fields.boolean('Uniek'),
        'categ_id': fields.many2one('res.function.categ', 'Functiecategorie', select=True, ondelete='cascade'),
                'unique_for_person' : fields.boolean('Uniek voor persoon'),
                'company_id': fields.many2one('res.company', 'Verantwoordelijke vzw'),
                'comment': fields.text('Notes'),
	}

        def write(self, cr, uid, ids, vals, context=None):
            """
            sync name function type with name in res.org.function
            double field exists to have an advanced filter field
            issue #1277
            """ 
            if 'name' in vals and vals['name']:
                res_org_fnc_obj = self.pool.get('res.organisation.function')
                for res_org_fnc_ids in res_org_fnc_obj.search(cr, uid, [('function_type_id', 'in', ids)]):
                    res_org_fnc_obj.write(cr, uid, [res_org_fnc_ids], {'name':vals['name']}, context=context)
                for res_org_fnc_ids in res_org_fnc_obj.search(cr, uid, [('function_type_id', 'in', ids),('active','=',False)]):
                    res_org_fnc_obj.write(cr, uid, [res_org_fnc_ids], {'name':vals['name']}, context=context)
            return super(res_function_type, self).write(cr, uid, ids, vals, context=context)

res_function_type()

# class res_radius_action(osv.osv):
# 	_name = 'res.radius.action'
# 	
# 	_columns = {
# 		'name': fields.char('Werkingsveld', size=128, required=True),
#         	'partner_ids': fields.many2many('res.partner', 'res_partner_radius_action_rel', 'radius_action_id', 'partner_id', 'Partners'),
# 	}
# 
# res_radius_action()

class res_niche_categ(osv.osv):
	_name = 'res.niche.categ'
	
	_columns = {
		'name': fields.char('Nichecategorie', size=128, required=True),
	}

res_niche_categ()

class res_niche(osv.osv):
	_name = 'res.niche'
	
	_columns = {
		'name': fields.char('Niche', size=128, required=True),
        #'partner_ids': fields.many2many('res.partner', 'res_partner_niche_rel', 'niche_id', 'partner_id', 'Partners'),
        'categ_id': fields.many2one('res.niche.categ', 'Nichecategorie', select=True, ondelete='cascade'),
	}

res_niche()

class res_organisation_relation(osv.osv):
	_name = 'res.organisation.relation'

	_columns = {
		'name': fields.char('Relatie', size=128, required=True),
		'organisation_type_ids': fields.many2many('res.organisation.type', 'res_organisation_type_relation_rel', 'relation_type_id', 'organisation_type_id', 'Organisatietypes'),
		'partner_ids': fields.many2many('res.partner', 'res_partner_relation_rel', 'relation_id', 'partner_id', 'Partners'),
        	'function_ids': fields.one2many('res.organisation.function', 'organisation_relation_id', 'Functies'),
		'valid_from_date': fields.date('Geldig van'),
		'valid_to_date': fields.date('Geldig tot'),
		'remittance_pct': fields.float('Afdracht'),
		'remittance_new_members': fields.float('Afdracht nieuwe leden'),
        	'partner_id': fields.many2one('res.partner', 'Partner', select=True, ondelete='cascade'),
	}

res_organisation_relation()

class res_organisation_function(osv.osv):
	_name = 'res.organisation.function'

	_columns = {
		'name': fields.char('Functietype', size=128, required=True),
		'organisation_relation_id': fields.many2one('res.organisation.relation', 'Organisatierelatie', select=True),
#		'partner_ids': fields.many2many('res.partner', 'res_partner_function_rel', 'function_id', 'partner_id', 'Partners'),
		'partner_id': fields.many2one('res.partner', 'Partner', select=True),
		'person_id': fields.many2one('res.partner', 'Persoon', select=True, required=True),
		'function_type_id': fields.many2one('res.function.type', 'Functietype', select=True),
		'valid_from_date': fields.date('Geldig van'),
		'valid_to_date': fields.date('Geldig tot'),
		'function_categ_id': fields.related('function_type_id','categ_id',type='many2one',relation='res.function.categ',string='Functiecategorie'),
	}

res_organisation_function()

class res_building_function(osv.osv):
	_name = 'res.building.function'
	
	_columns = {
		'name': fields.char('Functie gebouw', size=128, required=True),
	}

res_building_function()

class building_ownership(osv.osv):
	_name = 'building.ownership'
	
	_columns = {
		'name': fields.char('Eigendomssituatie', size=128, required=True),
	}

building_ownership()

# class building_spatial_planning(osv.osv):
# 	_name = 'building.spatial.planning'
# 	
# 	_columns = {
# 		'name': fields.char('Ruimtelijke ordening', size=128, required=True),
# 	}
# 
# building_spatial_planning()

class building_heritage(osv.osv):
	_name = 'building.heritage'
	
	_columns = {
		'name': fields.char('Beschermd onroerend erfgoed', size=128, required=True),
	}

building_heritage()

class building_insurance(osv.osv):
	_name = 'building.insurance'
	
	_columns = {
		'partner_id': fields.many2one('res.partner', 'Partner', select=True),
		'type': fields.many2one('building.insurance.type', 'Type verzekering', required=True),
		'provider': fields.many2one('res.partner', 'Leverancier'),
		'valid_from_date': fields.date('Geldig van'),
		'valid_to_date': fields.date('Geldig tot'),
		'analytic_account_id': fields.many2one('account.analytic.account', 'Kostenplaats'),
		'reference_number': fields.char('Polisnummer', size=128),
	}

building_insurance()

class building_insurance_type(osv.osv):
	_name = 'building.insurance.type'
	
	_columns = {
		'name': fields.char('Type verzekering', size=128, required=True),
		}

building_insurance_type()

class building_public_utility(osv.osv):
	_name = 'building.public.utility'
	
	_columns = {
		'partner_id': fields.many2one('res.partner', 'Partner', select=True),
		'type': fields.many2one('building.public.utility.type', 'Type contract', required=True),
		'provider': fields.many2one('res.partner', 'Leverancier', required=True),
		'nr_supply_point': fields.char('Uniek nummer afnamepunt', size=128),
		'valid_from_date': fields.date('Geldig van'),
		'valid_to_date': fields.date('Geldig tot'),
		'analytic_account_id': fields.many2one('account.analytic.account', 'Kostenplaats'),
		'reference_number': fields.char('Contract nummer', size=128),
		'date_latest_check': fields.date('Laatste keuring'),
		'remark_latest_check': fields.char('Opmerking laatste keuring', size=128),
	}

building_public_utility()

class building_public_utility_type(osv.osv):
	_name = 'building.public.utility.type'
	
	_columns = {
		'name': fields.char('Type contract', size=128, required=True),
		}

building_public_utility_type()

class res_partner(osv.osv):
	_name = 'res.partner'
	_inherit = 'res.partner'

	_columns = {
        'organisation_type_id': fields.many2one('res.organisation.type', 'Organisatietype', select=True),
        'building_function_id': fields.many2one('res.building.function', 'Functie gebouw', select=True),
        'building_capakey': fields.char('Capakey', size=128),
        'building_date_end': fields.date('Einddatum', size=128),
        'organisation_relation_ids': fields.many2many('res.partner', 'res_partner_organisation_rel', 'partner_id', 'relation_id', 'Relaties'),
        'organisation_relation_ids_inv': fields.many2many('res.partner', 'res_partner_organisation_rel', 'relation_id', 'partner_id', 'Relaties (vanuit partner)'),
        'relation_ids': fields.many2many('res.organisation.relation', 'res_organisation_relation_rel', 'partner_id', 'relation_id', 'Partners'),
        'partner_up_id': fields.many2one('res.partner', 'Bovenliggende relatie', select=True, ondelete='cascade'),
        'partner_down_ids': fields.one2many('res.partner', 'partner_up_id', 'Onderliggende relaties'),
		'organisation_function_parent_ids': fields.one2many('res.organisation.function', 'partner_id', 'Functies voor vzw'),
		'organisation_function_child_ids': fields.one2many('res.organisation.function', 'person_id', 'Functies voor persoon'),
        'niche_categ_ids': fields.many2many('res.niche.categ', 'res_organisation_niche_cat_rel', 'partner_id', 'categ_id', 'Niche Categorie'),
        #'niche_categ_ids': fields.many2many('res.niche.categ', 'res_organisation_niche_categ_rel', 'partner_id', 'niche_categ_id', 'Nichecategorie'),
        'niche_ids': fields.many2many('res.niche', 'res_organisation_niche_rel', 'partner_id', 'niche_id', 'Niches'),
        'zip_ids': fields.many2many('res.country.city', 'res_organisation_city_rel', 'partner_id', 'zip_id', 'Gemeentes'),
        'm2m_zip_ids': fields.many2many('res.country.city', 'res_organisation_city_m2m_rel', 'partner_id', 'zip_id', 'Gemeentes'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytische code', select=True, ondelete='cascade'),
        'regional_level': fields.selection([('L','Lokaal'),('G','Gewestelijk'),('R','Regionaal'),('P','Provinciaal')], string='Regionaal niveau', size=1),
        'nature_up_id': fields.many2one('res.partner', 'Bovenliggend natuurgebied', select=True, ondelete='cascade'),
		'remittance_new_member': fields.float('Afdracht nieuw lid'),
		'remittance_exist_member': fields.float('Afdracht bestaand lid'),
		'display_functions_company': fields.related('organisation_type_id','display_functions_company',type='boolean',string='Toon functies vzw'),
		'display_functions_person': fields.related('organisation_type_id','display_functions_person',type='boolean',string='Toon functies persoon'),
		'display_remittance': fields.related('organisation_type_id','display_remittance',type='boolean',string='Toon afdracht'),
		'display_relations': fields.related('organisation_type_id','display_relations',type='boolean',string='Toon relaties'),
		'display_relations_vertical': fields.related('organisation_type_id','display_relations_vertical',type='boolean',string='Toon verticale relaties'),
		'display_relations_horizontal': fields.related('organisation_type_id','display_relations_horizontal',type='boolean',string='Toon horizontale relaties'),
		#'display_radius_action': fields.related('organisation_type_id','display_radius_action',type='boolean',string='Toon werkingsveld'),
		'display_niche': fields.related('organisation_type_id','display_niche',type='boolean',string='Toon niche'),
		#'display_niche_category': fields.related('organisation_type_id','display_niche_category',type='boolean',string='Toon niche categorie'),
		'display_reference': fields.related('organisation_type_id','display_reference',type='boolean',string='Toon referentie'),
		'display_npca': fields.related('organisation_type_id','display_npca',type='boolean',string='Toon NPCA'),
		'display_regional_level': fields.related('organisation_type_id','display_regional_level',type='boolean',string='Toon regionaal niveau'),
		'display_nature_up': fields.related('organisation_type_id','display_nature_up',type='boolean',string='Toon bovenliggend natuurgebied'),
		'display_partner_up': fields.related('organisation_type_id','display_partner_up',type='boolean',string='Toon bovenliggende relatie'),
		'display_regional_definition': fields.related('organisation_type_id','display_regional_definition',type='boolean',string='Toon regionale definitie'),
		'display_regional_definition_m2m': fields.related('organisation_type_id','display_regional_definition_m2m',type='boolean',string='Toon regionale definitie (m2m)'),
		'display_analytic': fields.related('organisation_type_id','display_analytic',type='boolean',string='Toon analytische code'),
		'display_address': fields.related('organisation_type_id','display_address',type='boolean',string='Toon adres'),
		'regional_partnership': fields.boolean('Regionaal samenwerkingsverband'),
		'display_regional_partnership': fields.related('organisation_type_id','display_regional_partnership',type='boolean',string='Toon regionaal samenwerkingsverband'),
		'display_phone': fields.related('organisation_type_id','display_phone',type='boolean',string='Toon telefoonnummer'),
		'display_contacts': fields.related('organisation_type_id','display_contacts',type='boolean',string='Toon contacten'),
		'display_ownership': fields.related('organisation_type_id','display_ownership',type='boolean',string='Toon eigendomssituatie en toegankelijkheid'),
		'display_invoicing': fields.related('organisation_type_id','display_invoicing',type='boolean',string='Toon boekhouding'),
		'display_insurance': fields.related('organisation_type_id','display_insurance',type='boolean',string='Toon verzekeringen'),
		'display_suppliers': fields.related('organisation_type_id','display_suppliers',type='boolean',string='Toon nutsleveranciers'),
		'display_extra_info': fields.related('organisation_type_id','display_extra_info',type='boolean',string='Toon bijkomende info'),
		'display_building_function': fields.related('organisation_type_id','display_building_function',type='boolean',string='Toon functie gebouw'),
		'display_building_capakey': fields.related('organisation_type_id','display_building_capakey',type='boolean',string='Toon capakey gebouw'),
		'display_building_date_end': fields.related('organisation_type_id','display_building_date_end',type='boolean',string='Toon einddatum gebouw'),
		#gebouwen Contactpersonen
		'building_resp_id': fields.many2one('res.partner', 'Verantwoordelijke gebouw'),
		'building_user_ids': fields.many2many('res.partner', 'res_partner_user_rel', 'partner_id', 'building_user_id', 'Gebruiker gebouw'),
		#gebouwen Eigendomssituatie en toegankelijkheid
		'building_resp_vzw': fields.many2one('res.company', 'Verantwoordelijke vzw'),
		'building_ownership_id': fields.many2one('building.ownership', 'Eigendomssituatie'),
# 		'building_spatial_planning_id': fields.many2one('building.spatial.planning', 'Ruimtelijke ordening'),
		'building_spatial_planning': fields.text('Ruimtelijke ordening'),
		'building_to_break_down': fields.boolean('Af te breken'),
		'building_heritage_id': fields.many2one('building.heritage', 'Beschermd onroerend erfgoed'),
		'building_accessibility':fields.text('Toegankelijkheid'),
		#gebouwen Extra info 
		'building_asbestos': fields.selection([('J','Aanwezig'),('N','Niet aanwezig'),('O','Ongekend')], string='Asbest', default='O', size=1),
		'building_asbestos_remarks': fields.text('Opmerkingen asbest'),
		'building_remarks':fields.text('Andere opmerkingen'),
		#gebouwen Verzekeringen
		'building_insurance_required': fields.selection([('J','Ja'),('N','Nee'),('O','Ongekend')], string='Verzekering nodig', default='O', size=1),
		'building_insurance_ids': fields.one2many('building.insurance', 'partner_id', 'Verzekeringen'),
		'building_theft': fields.boolean('Diefstal'),
		'building_capital': fields.float('Kapitaal gebouw'),
		'building_capital_content': fields.float('Kapitaal inhoud'),
		'building_abex': fields.float('ABEX index'),
		'building_annual_prem': fields.float('Jaarpremie'),
		'building_extra_info':fields.text('Extra informatie'),
		#gebouwen Nutsvoorzieningen
		'building_public_utility_ids': fields.one2many('building.public.utility', 'partner_id', 'Nutsvoorzieningen'),
		#gebouwen Boekhouding
		'building_activa_nr': fields.many2one('account.asset.asset', 'Activanummer', select=True),
		'building_analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimensie 1', select=True),
		'building_analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimensie 2', select=True),
		'building_analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimensie 3', select=True),
	}

 	def write(self, cr, uid, ids, vals, context=None): 		
 		if 'organisation_relation_ids' in vals:
 			for partner in self.browse(cr,uid,vals['organisation_relation_ids'][0][2]):
 				partner_ids = [ids[0]]
 				for relation in partner.organisation_relation_ids:
 					 partner_ids.append(relation.id)
	 			partner_ids = list(set(partner_ids))
	 			partner_list = [6,False,partner_ids]
	 			vals_partner = {'organisation_relation_ids': [partner_list]} 				
	 			res = super(res_partner, self).write(cr, uid, partner.id, vals_partner, context=context)
	 		related_partners = self.search(cr,uid,[('organisation_relation_ids','in',ids[0])])
	 		for partner in self.browse(cr,uid,vals['organisation_relation_ids'][0][2]):
	 			if partner.id in related_partners: related_partners.remove(partner.id)
	 		if len(related_partners) > 0:
	 			for partner in related_partners:
		 			partner_ids = []
		 			for relation in self.search(cr,uid,[('organisation_relation_ids','in',partner)]):
	 					 partner_ids.append(relation)
	 				if ids[0] in partner_ids: partner_ids.remove(ids[0])
		 			partner_ids = list(set(partner_ids))
		 			partner_list = [6,False,partner_ids]
		 			vals_partner = {'organisation_relation_ids': [partner_list]} 				
		 			res = super(res_partner, self).write(cr, uid, partner, vals_partner, context=context)
	 			
	 		
	 	
  		if 'niche_ids' in vals:
 			#append bijhorende niche_cat_ids
 			print 'append niche_categ_ids to vals'
 			niche_obj = self.pool.get('res.niche')
 			cat_ids = []
 			for niche in niche_obj.browse(cr,uid,vals['niche_ids'][0][2]):
			 	cat_ids.append(niche.categ_id.id)
			cat_ids = list(set(cat_ids))
			cat_list = [6,False,cat_ids]
 			vals['niche_categ_ids'] = [cat_list]
 		res = super(res_partner, self).write(cr, uid, ids, vals, context=context)
 		return res

res_partner()

class res_country_city(osv.osv):
	_inherit = 'res.country.city'

	_columns = {
        	'org_partner_ids': fields.many2many('res.partner', 'res_organisation_city_rel', 'zip_id', 'partner_id', 'Afdelingen'),
        	'org_partner_m2m_ids': fields.many2many('res.partner', 'res_organisation_city_m2m_rel', 'zip_id', 'partner_id', 'Organisatiestructuur'),
	}

res_country_city()

class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'

    _columns = {
    }

    def write(self, cr, uid, ids, vals, context=None):
        res = super(account_analytic_account, self).write(cr, uid, ids, vals, context=context)

	for analytic_account_id in ids:
            if 'name' in vals:
                sql_stat = "update res_partner set name = '%s' where analytic_account_id = %d" % (vals['name'].replace("'","''"), analytic_account_id, )
                cr.execute(sql_stat)

        return res
