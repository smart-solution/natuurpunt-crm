from osv import osv
from osv import fields
from openerp.tools.translate import _
import math
import hashlib

ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
def alphaID(idnum, to_num=False, pad_up=False, passkey=None):
  index = ALPHABET
  if passkey:
    i = list(index)
    passhash = hashlib.sha256(passkey).hexdigest()
    passhash = hashlib.sha512(passkey).hexdigest() if len(passhash) < len(index) else passhash
    p = list(passhash)[0:len(index)]
    index = ''.join(zip(*sorted(zip(p,i)))[1])
  base = len(index)
  if to_num:
    idnum = idnum[::-1]
    out = 0
    length = len(idnum) -1
    t = 0
    while True:
      bcpow = int(pow(base, length - t))
      out = out + index.index(idnum[t:t+1]) * bcpow
      t += 1
      if t > length: break
    if pad_up:
      pad_up -= 1
      if pad_up > 0:
        out -= int(pow(base, pad_up))
  else:
    if pad_up:
      pad_up -= 1
      if pad_up > 0:
        idnum += int(pow(base, pad_up))
    out = []
    t = int(math.log(idnum, base))
    while True:
      bcp = int(pow(base, t))
      a = int(idnum / bcp) % base
      out.append(index[a:a+1])
      idnum = idnum - (a * bcp)
      t -= 1
      if t < 0: break
    out = ''.join(out[::-1])
  return out

class gelukscode(osv.osv_memory):
    _name = 'gelukscode'
    _description = 'gelukscode'
    _columns = {
                'title': fields.char(string="Title", size=100, readonly=True),
                'message': fields.text(string="Message", readonly=True),
                }
    _req_name = 'title'

    def _get_view_id(self, cr, uid):
        """Get the view id
        @return: view id, or False if no view found
        """
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'natuurpunt_gelukscode', 'gelukscode_form')
        return res and res[1] or False

    def messagebox_gelukscode(self, cr, uid, title, message, context=None):
        id = self.create(cr, uid, {'title': title, 'message': message})
        res = {
               'name': 'Gelukscode: %s' % _(title),
               'view_type': 'form',
               'view_mode': 'form',
               'view_id': self._get_view_id(cr, uid),
               'res_model': 'gelukscode',
               'domain': [],
               'context': context,
               'type': 'ir.actions.act_window',
               'target': 'new',
               'res_id': id
               }
        return res

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def manually_generate_gelukscode(self, cr, uid, ids, context=None):
        title = ''
        passkey = self.pool.get('ir.config_parameter').get_param(cr, uid, 'gelukscode_passkey')
        gelukscode = ''
        for partner in self.browse(cr, uid, ids, context=context):
           title = partner.name
           membership_nbr = int(partner.membership_nbr.encode('ascii','ignore'))
           gelukscode = alphaID(membership_nbr, pad_up=3, passkey=passkey)[:2]
        if gelukscode:
            return self.pool.get('gelukscode').messagebox_gelukscode(cr, uid, title=title, message=partner.membership_nbr+gelukscode)
        else:
            return False