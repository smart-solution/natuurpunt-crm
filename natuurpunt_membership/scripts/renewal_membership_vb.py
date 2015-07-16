# -*- coding: utf-8 -*-
import xmlrpclib

server='localhost'
dbname7='natuurpunt'
uid=1
pwd7='n2aevl8w'
model = 'res.partner'


sock7 = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/object'%(server))

ids = sock7.execute(dbname7, uid, pwd7, model, 'search', []) 

a_datas = sock7.execute(dbname7, uid, pwd7, model, 'read', ids, ['membership_state','membership_stop','free_member','state_id'])

count = 0
count100 = 0

for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 54:
        sock7.execute(dbname7, uid, pwd7, model, 'create_membership_invoice', [a_data['id']], 2, {'membership_product_id': 2, 'amount': 24.0, 'membership_renewal': True}, {})
        count += 1
        count100 += 1
        if count100 == 100:
	    print 'Processed:', count
	    count100 = 0

print 'Totaal Vlaams-Brabant:', count

