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
from openerp import netsvc
import time
import re
from datetime import datetime
import datetime as timetools
import logging
import cStringIO
import base64, os
from tempfile import mkstemp
from contextlib import contextmanager
from natuurpunt_tools import get_included_product_ids

logger = logging.getLogger(__name__)

class payment_line(osv.osv):
    _inherit = 'payment.line'

    def create(self, cr, uid, vals, context=None):
        if 'move_line_id' in vals and vals['move_line_id']:
            move_obj = self.pool.get('account.move.line')
            move_id = move_obj.search(cr, uid, [('id', '=', vals['move_line_id'])])
            if move_id and len(move_id) > 0:
                move_line_id = move_obj.browse(cr, uid, move_id[0])
                invoice_obj = self.pool.get('account.invoice')
                invoice_id = invoice_obj.search(cr, uid, [('move_id', '=', move_line_id.move_id.id)])
                if invoice_id and len(invoice_id) > 0:
                    invoice = invoice_obj.browse(cr, uid, invoice_id[0])
                    if invoice.journal_id.code == 'LID':
                        vals['communication'] = 'Lidmaatschap'
                    if invoice.journal_id.code == 'GIFT':
                        if invoice.donation_id and invoice.donation_id.analytic_account_id:
                            vals['communication'] = 'Gift %s' % (invoice.donation_id.analytic_account_id.name, )
                        else:
                            vals['communication'] = 'Gift TO CHECK'
                    if invoice.sdd_mandate_id:
                        vals['bank_id'] = invoice.sdd_mandate_id.partner_bank_id.id
                        vals['sdd_mandate_id'] = invoice.sdd_mandate_id.id

        return super(payment_line, self).create(cr, uid, vals, context=context)

payment_line()

def invoice_partner_renewal(obj,cr,uid,partner_id,context=None):
    """
    Create renewal membership invoice and commit transaction
    Use renewal product if set else get a default from the membership lines
    """
    product_obj = obj.pool.get('product.product')
    partner_obj = obj.pool.get('res.partner')
    datas = {}
    partner = partner_obj.browse(cr, uid, partner_id)
    if partner.membership_renewal_product_id and partner.membership_renewal_product_id.membership_product:
        datas = {
            'membership_product_id': partner.membership_renewal_product_id.id,
            'amount': partner.membership_renewal_product_id.list_price,
        }
    else:
        default_renewal_product = get_included_product_ids(product_obj,cr,uid,False)
        for product in product_obj.browse(cr, uid, default_renewal_product, context=context):
            datas = {
                'membership_product_id': product.id,
                'amount': product.list_price,
            }
    datas['membership_renewal'] = True
    invoice_id = partner_obj.create_membership_invoice(cr, uid, [partner.id], datas=datas, context=context)
    cr.commit()
    return invoice_id

class wizard_partner_to_renew(osv.osv_memory):
    _name = 'wizard.partner.to.renew'

    _columns = {
        'end_date_membership': fields.date('Einddatum Lidmaatschap'),
        'export': fields.boolean('Export via csv'),
    }

    defaults = {
        'end_date_membership': time.strftime('%Y-%m-%d'),
    }

    def find_members_to_renew(self, cr, uid, ids, context=None):
        partner_obj = self.pool.get('res.partner')
        mod_obj = self.pool.get('ir.model.data')
        membership_obj = self.pool.get('membership.membership_line')

        wiz = self.browse(cr, uid, ids)[0]

        end_date_membership = wiz.end_date_membership
        if not end_date_membership:
            end_date_membership = datetime.today().strftime('%Y-12-31')
        end_date_membership = datetime.strptime(end_date_membership,'%Y-%m-%d')

        args = [('deceased','=',False),
                ('free_member','=',False),
                ('third_payer_id','=',False),
                ('active','=',True),]

        def read_partners():
            partner_ids = partner_obj.search(cr, uid, args=args, context=context)
            for partner in partner_obj.read(cr, uid, partner_ids, ['membership_state'], context=context):
                yield partner

        def get_partners_to_renew(partners):
            csv_buf = cStringIO.StringIO() if wiz.export else False
            member_ids = []
            counter = 0
            logger.info('Calculation of renwal membership started')
            for partner_dict in partners:
                counter = counter + 1
                if counter%1000 == 0:
                    logger.info('Calculated {} renwal memberships'.format(counter))
                if partner_dict['membership_state'] == 'paid':
                    # Check if partner has paid or invoiced membership after end_date_membership
                    renew_date = (end_date_membership + timetools.timedelta(days=1)).strftime('%Y-%m-%d')
                    partner = partner_obj.browse(cr, uid, partner_dict['id'], context=context)
                    mline, membership_state_field = partner_obj._np_membership_state(cr, uid, partner, date=renew_date, context=context)
                    if mline == None:
                        continue
                    if membership_state_field in ['paid','invoiced','wait_member','canceled'] or (mline.membership_cancel_id.id or mline.date_cancel):
                        continue
                    else:
                        if csv_buf:
                            line = u''.join((str(partner.id),'|',partner.name,'|',membership_state_field)).encode('utf-8').strip()
                            csv_buf.write(line+'\n')
                        member_ids.append(partner_dict['id'])
                else:
                    continue
            logger.info('Calculation of renwal membership finshed')
            if csv_buf:
                out = base64.encodestring(csv_buf.getvalue())
                csv_buf.close()
            else:
                out = False
            return member_ids, out

        partners_to_renew, feedback_csv = get_partners_to_renew(read_partners())

        if feedback_csv:
            return self.pool.get('wizard.partner.to.renew.feedback').renew_feedback(cr, uid, ids=partners_to_renew, feedback_stream=feedback_csv)
        else:
            try:
                tree_view_id = mod_obj.get_object_reference(cr, uid, 'membership', 'membership_members_tree')[1]
            except ValueError:
                tree_view_id = False
            try:
                form_view_id = mod_obj.get_object_reference(cr, uid, 'base', 'view_partner_form')[1]
            except ValueError:
                form_view_id = False

            return {'name': _('Niet-hernieuwde leden vinden'),
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'res.partner',
                    'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                    'type': 'ir.actions.act_window',
                    'domain': [('id','in',partners_to_renew)]
            }

class wizard_partner_to_renew_feedback(osv.osv_memory):
    _name = 'wizard.partner.to.renew.feedback'
    _description = 'feedback wizard.partner.to.renew'
    _columns = {
        'title': fields.char(string="Title", size=100, readonly=True),
        'message': fields.text(string="Message", readonly=True),
        'feedback_stream': fields.binary('Feedback File Stream', readonly=True),
        'feedback_fname': fields.char('File name', size=40),
    }
    _req_name = 'title'

    partner_ids = []

    def put_members_to_renew(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        try:
            tree_view_id = mod_obj.get_object_reference(cr, uid, 'membership', 'membership_members_tree')[1]
        except ValueError:
            tree_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'base', 'view_partner_form')[1]
        except ValueError:
            form_view_id = False

        return {'name': _('Niet-hernieuwde leden vinden'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'res.partner',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'type': 'ir.actions.act_window',
                'domain': [('id','in',wizard_partner_to_renew_feedback.partner_ids)]}

    def _get_view_id(self, cr, uid):
        """Get the view id
        @return: view id, or False if no view found
        """
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                'natuurpunt_mandate_ext', 'partner_to_renew_feedback_view')
        return res and res[1] or False

    def message(self, cr, uid, id, context):
        message = self.browse(cr, uid, id)
        res = {
               'name': 'Feedback niet-hernieuwde leden',
               'view_type': 'form',
               'view_mode': 'form',
               'view_id': self._get_view_id(cr, uid),
               'res_model': 'wizard.partner.to.renew.feedback',
               'domain': [],
               'context': context,
               'type': 'ir.actions.act_window',
               'target': 'new',
               'res_id': message.id
        }
        return res

    def renew_feedback(self, cr, uid, ids, feedback_stream, context=None):
        title='Feedback hernieuwen leden'
        message = 'Aantal te hernieuwen leden : {}'.format(len(ids))
        wizard_partner_to_renew_feedback.partner_ids = ids 
        id = self.create(cr, uid, {'title': title, 'message': message,
                                   'feedback_stream': feedback_stream,
                                   'feedback_fname': 'partner_renew.csv'})
        res = self.message(cr, uid, id, context)
        return res

class CSVException(Exception):
        pass

class membership_renew(osv.osv_memory):
    """Membership renew"""

    _name = "membership.renew"
    _description = "Membership Renew Wizard"

    _columns = {
        'import_file': fields.binary('Import File'),
    }

    @contextmanager
    def partners_src(self,cr,uid,ids,context=None):
        logger.info('CREATE of renwal membership started')
        data = self.read(cr, uid, ids)[0]
        if data['import_file']:
            file_data = data['import_file']
            (fileno, fp_name) = mkstemp('.csv', 'openerp_')

            try:
                os.write(fileno,base64.decodestring(file_data))
                os.close(fileno)
            except (IOError, OSError):
                raise osv.except_osv(_('IOError/OSError'), _('File can not be imported !'))

            # universal-newline mode
            csv_in_file = open(fp_name, 'U')
            yield csv_in_file
            os.remove(fp_name)
            print "temp file removed"
        else:
            yield context.get('active_ids', [])
        logger.info('CREATE of renwal membership finished')

    def membership_renew(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}

        renew_list = []

        with self.partners_src(cr,uid,ids,context) as partners:
            for partner in partners:
                if not isinstance(partner, int):
                    try:
                        record_list = partner.strip().split('|')
                    except Exception:
                        raise CSVException(_('CSV split error'))

                    try:
                        partner_id = int(record_list[0])
                    except IndexError:
                        raise CSVException(_('CSV index error'))
                else:
                    partner_id = partner
                logger.info('CREATE renewal membership for partner {}'.format(partner_id))
                renew_list.append(invoice_partner_renewal(self,cr,uid,partner_id,context=context))

        try:
            search_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_account_invoice_filter')[1]
        except ValueError:
            search_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')[1]
        except ValueError:
            form_view_id = False

        return  {
            'domain': [('id', 'in', renew_list)],
            'name': 'Renew Membership',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_id, 'form')],
            'search_view_id': search_view_id,
        }

        return True

membership_renew()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
