#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
{
    "name" : "natuurpunt_imp_members",
    "version" : "1.0",
    "author" : "SmartSolution",
    "category" : "Generic Modules/Base",
    "description": """
""",
    "depends" : ["base","natuurpunt_membership"],
    "update_xml" : [
        'natuurpunt_imp_members_view.xml',
        'security/natuurpunt_imp_members_security.xml',
        'security/ir.model.access.csv',
        ],
    "active": False,
    "installable": True
}
