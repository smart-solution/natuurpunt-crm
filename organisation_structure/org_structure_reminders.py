# -*- coding: utf-8 -*-
##############################################################################
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

import datetime, re, random

from openerp.tools.translate import _
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from natuurpunt_tools import get_eth0
from openerp import SUPERUSER_ID

class organisation_structure_reminder(osv.osv_memory):

    _name = 'organisation.structure.reminder'

    def send_organisation_structure_reminders_email(self, cr, uid, email_to, msg_vals, context=None):
        """Send organisation structure reminders via e-mail"""

        if email_to:
            try:
                data_obj = self.pool.get('ir.model.data')
                template = data_obj.get_object(cr, uid, 'organisation_structure', 'email_template_organisation_structure_reminder')
            except ValueError:
                raise osv.except_osv(_('Error!'),_("Cannot send email: no email template configured.\nYou can configure it under Settings/Technical/Email."))
            assert template._name == 'email.template'
            context['subject']   = msg_vals['subject']
            context['email_to']  = email_to
            context['body_html'] = msg_vals['body']
            context['body']      = msg_vals['body']
            context['res_id']    = False

            self.pool.get('email.template').send_mail(cr, uid, template.id, False, force_send=True, context=context)

        return True

    def generate_building_reminders(self, cr, uid, context=None):
        """Generates building reminders"""
        if context == None:
            context = {}

        msg_obj = self.pool.get('mail.message')
        building_obj = self.pool.get('res.partner')
        organisation_type_obj = self.pool.get('res.organisation.type')

        time_now = datetime.datetime.today().strftime('%Y-%m-%d')

        building_type_ids = organisation_type_obj.search(cr, uid, [('name','=','Gebouw')])

        domain_filter = [('organisation_type_id', 'in', building_type_ids),
                         ('building_date_end','=',time_now)]

        building_ids = building_obj.search(cr, uid, domain_filter)
        buildings = []

        html_body_end = "<span><p><p/>"+_('Send from host %s - db %s')%(get_eth0(),cr.dbname)+"</span>"
        link = "<b><a href='{}?db={}#id={}&view_type=form&model={}&menu_id={}&action={}'>{}</a></b><br>"
        base_url = self.pool.get('ir.config_parameter').get_param(cr, SUPERUSER_ID, 'web.base.url')
        for building in building_obj.browse(cr, uid, building_ids):
            buildings.append([building.id,building.name])

        #context.update({'lang': user.lang})

        if buildings:
            building_links = ""
            for building in buildings:
                building_links += link.format(base_url,cr.dbname,building[0],'res.partner',507,598,building[1])
            body = _("{0} gebouw(en) {1} {2}").format(len(buildings),_('hebben hun einddatum bereikt:<br>'),building_links)
            msg_vals = {
                'subject': "Gebouwen met einddatum {0}".format(time_now),
                'body': body + html_body_end,
                'type': 'notification',
                'notified_partner_ids': [],
            }
            msg_obj.create(cr, uid, msg_vals)
            self.send_organisation_structure_reminders_email(cr, uid, 'financien@natuurpunt.be', msg_vals, context=context)

        return True

