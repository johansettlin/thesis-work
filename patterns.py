from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
from graph_api import *

#Caller for pw-reuse pattern
def passwordReuse(g):
    ap = passwordReuseAP(g)
    passwordReuseEP(g, ap)
#An anti pattern (AP) returns a list of affected vertices (or edges)
def passwordReuseAP(g):
    ap = g.V().match(\
        __.as_("credential").out("instanceOf").hasLabel("Credentials"),\
        __.as_("credential").out().where(__.out("instanceOf").hasLabel("Identity")).as_("Identity")).\
    select("credential", "Identity").toList()
                    #__.as_("Identity").out().where(__.out("instanceOf").hasLabel("Application")).count().is_(P.gte(2))).\
            
    #print("Pattern: ",ap)
    return ep
#Exchange Patterns is a set of funtion calls to the graph_api
def passwordReuseEP(g, ap):
    for p in ap:
        changes = {"objects": [], "associations": []}
        #Do something with the vertecies in ap
        ## (1) add new objects
        obj1, valid = addObject(g, "idx", "Identity")
        ## (2) add new assocs
        assoc1, valid = addAssociation(g, obj1, p['Identity'], "CanAssume")
        ## (3) set properties /remove or assets
        activateDefense(g, obj1, "twoFactorAuthentication")
        


        