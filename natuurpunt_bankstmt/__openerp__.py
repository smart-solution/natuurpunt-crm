# -*- encoding: utf-8 -*-
{
	"name" : "Natuurpunt Bank Statement",
	"version" : "1.0",
	"author" : "Smart Solution",
	"description" : "This module updates the account number always based upon the selected partner.",
	"website" : "http://",
	"category" : "Account",
	"depends" : ["account","natuurpunt_coda","natuurpunt_account","l10n_be_coda","multi_analytical_account","natuurpunt_membership","base_iban"],
	"init_xml" : [],
	"demo_xml" : [],
	"update_xml" : ["natuurpunt_bankstmt_view.xml"],
	"installable": True
}
