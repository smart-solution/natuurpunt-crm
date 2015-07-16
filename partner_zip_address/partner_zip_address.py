#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
##############################################################################

from openerp.osv import osv, fields

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def onchange_zip_id(self, cr, uid, ids, zip_id, context=None):
        res = {}
        if not zip_id:
            res['street'] = ""
            res['city'] = ""
            res['country_id'] = ""
            res['zip'] = ""
        else:
            city_obj = self.pool.get('res.country.city')
            city = city_obj.browse(cr, uid, zip_id, context=context)
            res['city'] = city.name
            res['country_id'] = city.country_id.id
            res['zip'] = city.zip
            for idn in ids:
                if idn == 160033 and city.zip == '8890':
                    res['city'] = 'Dadizele'
            res['street'] = ""
            res['street_nbr'] = ""
            res['street_bus'] = ""
            res['street_id'] = False

        print 'RES:',res
        return {'value':res}

    def onchange_street_id(self, cr, uid, ids, zip_id, street_id, street_nbr, street_bus, context=None):
        res = {}
        if not street_id:
            res['street'] = ""
        else:
            street_obj = self.pool.get('res.country.city.street')
            street = street_obj.browse(cr, uid, street_id, context=context)
            if street_nbr and street_bus:
                res['street'] = street.name + ' ' + street_nbr + '/' + street_bus
            else:
                if street_nbr:
                    res['street'] = street.name + ' ' + street_nbr
                else:
                    res['street'] = street.name

        print 'RES:',res
        return {'value':res}

    _columns = {
		'zip_id': fields.many2one('res.country.city', 'Gemeente ID'),
		'street_id': fields.many2one('res.country.city.street', 'Straat ID'),
		'street_nbr': fields.char('Huisnummer', size=16),
		'street_bus': fields.char('Bus', size=16),
    }

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

