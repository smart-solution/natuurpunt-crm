# -*- encoding: utf-8 -*-
{
	"name" : "Natuurpunt Sepa Rejects",
	"version" : "1.0",
	"author" : "Smart Solution",
	"description" : "This module processes the SEPA rejects.",
	"website" : "http://",
	"category" : "Account",
	"depends" : ["natuurpunt_sepa","natuurpunt_bankstmt"],
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["natuurpunt_rejects_view.xml","security/ir.model.access.csv"],
	"installable": True
}
