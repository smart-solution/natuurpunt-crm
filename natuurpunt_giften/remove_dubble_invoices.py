# -*- coding: utf-8 -*-
import xmlrpclib

server='localhost'
dbname='natuurpunt_prod_1_7_1'
uid=1
pwd='n2aevl8w'

#replace localhost with the address of the server
sock = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/object'%(server))
ids = sock.execute(dbname, uid, pwd, 'account.invoice', 'search', [('partner_id','=',160881),('id','!=',128763),('id','!=',234072),('state','=','open')]) 
print "IDS:",ids

#for a_data in a_datas:
sock.execute(dbname, uid, pwd, 'account.invoice', 'action_cancel', ids)

print "DOUBLE PROCESS DONE"
