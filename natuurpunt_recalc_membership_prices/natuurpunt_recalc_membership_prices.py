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
import logging

logger = logging.getLogger(__name__)

price_dict = {
    2 : 30.0,
    5 : 51.0,
    6 : 43.0,
    7 : 42.0,
    8 : 21.0,
    3 : 13.0,
    4 : 12.0,
    204 : 15.0,
    205 : 45.0,
    206 : 66.0,
    207 : 58.0,
    208 : 57.0,
    209 : 36.0,
    210 : 28.0,
    211 : 27.0
}

class product_product(osv.osv):
    _inherit = 'product.product'

    def recalc_membership_prices(self, cr, uid, product_id, context=None):
        product = self.browse(cr, uid, [product_id], context=context)[0]
        return self.write(cr, uid, product_id, {'list_price': price_dict[product_id]}, context=context)

    def _recalc_membership_prices(self, cr, uid, context=None):
        logger.info('Calculation of membership prices started')
        product_ids = self.search(cr, uid, ['|',('membership_product','=',True),('magazine_product','=',True)], context=context)
        if product_ids:
            for product in product_ids:
                self.recalc_membership_prices(cr, uid, product, context=context)
        logger.info('Calculation of membership prices ended')
        return True

product_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
