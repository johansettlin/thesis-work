from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import Cardinality, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from graph_api import *

def exchangePattern1(g):
    ## BAD PATTERN ##
    p = g.V().match(__.as_("cred").where(__.out("instanceOf").hasLabel("Credentials")),\
                    
                    __.as_("cred").out("identities").where(__.out("instanceOf").hasLabel("Identity")).as_("id"),\
                    
                    __.not_(__.as_("cred").out().\
                        where(__.out("instanceOf").hasLabel("Data").out().as_("id"))))\
                .select("cred", "id").toList()
    ## REWRITE PATTERN
    for a in p:
        removeAssociation(g, a['cred'], a['id'], "identities")
        data = addNewObject(g, "Data", "data")
        addNewAssociation(g, a['cred'], data, "EncryptionCredentials")
        addNewAssociation(g, data, a['id'], "ReadPrivileges")

        success = validatePatternExchange(g)
        if(success):
            activateDefense(g, data, "authenticated")

    def getExchangePatterns1():
        return [exchangePattern1]