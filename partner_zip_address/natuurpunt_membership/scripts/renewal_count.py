# -*- coding: utf-8 -*-
import xmlrpclib

server='localhost'
dbname7='natuurpunt'
uid=1
pwd7='n2aevl8w'
model = 'res.partner'


sock7 = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/object'%(server))

ids = sock7.execute(dbname7, uid, pwd7, model, 'search', []) 

a_datas = sock7.execute(dbname7, uid, pwd7, model, 'read', ids, ['id','name','membership_state','membership_stop','free_member','state_id'])

count = 0

count_bxl = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 52:
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_bxl += 1
print 'Totaal Brussel:', count_bxl

count_vb = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 54:
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_vb += 1
#	print a_data['id'], ' ', a_data['name'], ' ', a_data['membership_stop']
print 'Totaal Vlaams-Brabant:', count_vb

count_ant = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 55:
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_ant += 1
print 'Totaal Antwerpen:', count_ant

count_lim = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 56:
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_lim += 1
print 'Totaal Limburg:', count_lim

count_wvl = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 61:
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_wvl += 1
print 'Totaal West-Vlaanderen:', count_wvl

count_ovl = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and a_data['state_id'] and a_data['state_id'][0] == 62:
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_ovl += 1
print 'Totaal Oost-Vlaanderen:', count_ovl

count_rest = 0
for a_data in a_datas:
    if a_data['membership_state'] != 'canceled' and a_data['membership_stop'] == '2014-12-31' and a_data['free_member'] != True and (not(a_data['state_id']) or (a_data['state_id'] and a_data['state_id'][0] != 52 and a_data['state_id'][0] != 54 and a_data['state_id'][0] != 55 and a_data['state_id'][0] != 56 and a_data['state_id'][0] != 61 and a_data['state_id'][0] != 62)):
#    sock7.execute(dbname7, uid, pwd7, model, 'write', [a_data['id']], {'date_from':a_data['date_from']})
        count += 1
	count_rest += 1
print 'Totaal Rest:', count_rest

print 'Totaal hernieuwingen:', count

