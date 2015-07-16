# -*- coding: utf-8 -*-
import xmlrpclib

server='localhost'
dbname7='natuurpunt'
uid=1
pwd7='n2aevl8w'
model = 'membership.membership_line'


sock7 = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/object'%(server))

ids = sock7.execute(dbname7, uid, pwd7, model, 'search', []) 

a_datas = sock7.execute(dbname7, uid, pwd7, model, 'read', ids, ['date_from'])

count = 0
count100 = 0

for a_data in a_datas:
    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
    count += 1
    count100 += 1
    if count100 == 100:
	print 'Processed:', count
	count100 = 0

print 'Total processed:', count

