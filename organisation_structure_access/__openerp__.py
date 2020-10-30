#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
{
    "name" : "organisation structure access",
    "version" : "1.0",
    "author" : "Joeri Belis",
    "category" : "base",
    "description": """Organisation Structure Access Management
""",
    "depends" : ["organisation_structure",],
    "data" : [
        'organisation_structure_access_view.xml',
        ],
    "update_xml" : [
        'security/ir.model.access.csv'
        ],
    "active": False,
    "installable": True
}
