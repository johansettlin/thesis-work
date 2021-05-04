from gremlin_python import statics
from gremlin_python.structure.graph import Graph
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
#from graphModels import exampleModel
from graphModels import xmlToModel, mal, addAssets, readMALSpec, drop_all, addAssociations
from graph_api import addObject, activateDefense, addAssociation, addNewObject, addNewAssociation
from patterns import *


def exampleGraph(g):
    exampleModel(g)
    bandName = g.V().has("Name", "Johan").out("member").values("Name").next()
    print(bandName)
    testMatch = g.V().match(__.as_("a").hasLabel("Person"), \
                            __.as_("a").out().hasLabel("Band").as_("b"),\
                            __.as_("a").out().hasLabel("Instrument").has("Type","Guitar"),\
                            __.as_("b").out().hasLabel("Festival").as_("c")).\
                        select("a", "c").by("Name").by("Location").toList()
    print(testMatch)

# A pattern consists of (i) a anti pattern (ii) a set of operations to apply the safe pattern on the anti-pattern

def patternReplacementAlgorithm(g, patterns):
    for pattern in pattern:
        #Check the applicability of the pattern in G
        antiPattern = pattern[0](g)
        if not (empty(antiPattern)):
            ##pattern is applicable
            #Gi = applyPy pattern
            pattern[1](g)
        else:
            #Pattern is not applicable
            break

def pattern2(g):
    antiPattern = g.V().match(__.as_("a").hasLabel("Application"),\
                              __.as_("a").where(__.not_(__.out().hasLabel("Application")))).\
                        select("a").toList()
    print(antiPattern)
    print(g.V(antiPattern[1].id).valueMap().next())
    return antiPattern
def rewrite(g, subgraph):
    for s in subgraph:
        #addVertex(g, g.V(s).)
        g.V(s)

def pattern1(g):
    ####Kanske ta först en identity som har två applicatio out och replacea en av de,
    #### så hitta c-i-ax2, ta första i den listan av apps och ta bort edgen mellan i-a
    ### skapa en ny med c-i-a1
    ###                 - ix-a2
    ### Sen kör detta iterativt???
    #Select the parts of the antipattern that will be changes
    antiPattern = g.V().match(__.as_("a").hasLabel("Credentials"), \
                              __.as_("a").out().hasLabel("Identity").as_("b"),\
                              __.as_("b").out().hasLabel("Application").count().is_(P.gte(2)),\
                              __.as_("b").out().hasLabel("Application").fold().as_("c")).\
                        select("b","c").toList()
    print(antiPattern)
    return antiPattern
    #The secure pattern would be one credential per identity 
    #(this is a special pattern due to we dont know how many new credentials that needs to be added)
def test(g):
    #### MAL Layer Testing ####
    print("--------MAL LAYER TESTING--------")
    vertices = g.V().hasLabel("root").out().project("label").by(T.label).toList()
    print("MAL Layer has vertices: ", [v['label'] for v in vertices])
    

    #The assets vertex should have a instanceProperies edge to a vertex with label name and tag
    print("instanceProperties for assets is name and tag: " , g.V().hasLabel("root").out("assets").out("instanceProperties").project("label").by(T.label).toList())
    #Attack steps should have DSLProperties type
    print("DSLProperties for attack steps is type: " ,  g.V().hasLabel("root").out("attackSteps").out("DSLProperties").project("label").by(T.label).toList())
    #### DSL Layer Testing ####
    print("--------DSL LAYER TESTING--------")
    #aStep = g.V().hasLabel("Data").out("attackSteps").toList()
    #print(g.V(aStep[0].id).values().next())
    ass = g.V().hasLabel("root").out("assets").in_("instanceOf").project("asset").by(T.label).toList()
    print("DSL Layer has assets: ", [a['asset'] for a in ass])

    #The assocs
    print("The assoc in the DSL Layer: ", g.V().hasLabel("root").out("associations").in_("instanceOf").label().toList())
    #### Instance Layer Testing ####
    print("--------INSTANCE LAYER TESTING--------")
    #Get all the objects in the instance model
    objectNames = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").values("name").toList()
    print("Model objects", objectNames)

    nrOfAttackSteps = g.V().hasLabel("root").out("attackSteps").in_("instanceOf").in_("instanceOf").count().next()
    nrOfConnAS  = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").out("attackStep").count().next()
    print("number of attacksteps in instance: ", nrOfAttackSteps, "nr of conn. attackstep: ",  nrOfConnAS)
    numberOfinstances = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").count().next()
    print("number of objects: ", numberOfinstances)
    #the properties of the objects 
    obj = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").properties().toList()
    #print("object props: ", obj)
    
    #Check the TTC-5% values of attack steps
    ttc = g.V().hasLabel("root").out("assets").in_("instanceOf").in_("instanceOf").out("attackStep").project("attackStep", "value").by(__.out("instanceOf").label()).by(__.values("TTC-5%")).toList()
    #print("TTC-5% values: ", ttc)

    print("The neighbours of OS: ", g.V().has("name", "OS").outE().where(__.inV().out("instanceOf").out("instanceOf").hasLabel("assets")).inV().properties("name").toList())


    ## API Test ##
    print("--------API TESTING--------")
    o = addObject(g, "test", "Identity")
    cred = addObject(g, "creden", "Credentials")
    print("Added object: " , g.V(o.id).properties("name").toList())
    print("Attack steps are: ", g.V(o.id).out("attackStep").out("instanceOf").project("AttackStep").by(T.label).toList())
    print("Defenses are: ", g.V(o.id).out("defense").out("instanceOf").project("Defense").by(T.label).toList())

    activateDefense(g, o, "disabled")
    print("Active defenses are: ", g.V(o.id).out("defense").where(__.has("active", 1)).out("instanceOf").project("defense").by(T.label).toList())

    print("test getting label: ", g.V(o.id).out("instanceOf").label().next())
    print("Test if a link exists: ",g.V(cred.id).out("instanceOf").out("associations").toList())
    addAssociation(g, o, cred, "IdentityCredentials")
    ap =passwordReuseAP(g)

if __name__ == "__main__":
    
    g = traversal().withRemote(DriverRemoteConnection('ws://localhost:8182/gremlin', 'g'))
    #exampleGraph(g)
    drop_all(g)
    #xmlToModel(g, './data-models/example-coreLang.sCAD')
    #pattern1(g)
    #pattern2(g)

    #MAL layer
    mal(g)

    #DSL layer
    assets, assocs = readMALSpec()
    addAssets(g, assets)
    addAssociations(g, assocs)

    #instance layer
    xmlToModel(g, './data-models/pw-reuse.sCAD', './data-models/pw-reuse.csv')


    o = addNewObject(g, "Identity", "id100")
    o2 = addNewObject(g, "Data", "datax")
    addNewAssociation(g, o, o2, "ReadPrivileges")

    #Validate an object
    check = g.V(o.id).outE().where(__.and_(__.inV().out("instanceOf").out("instanceOf").hasLabel("assets"), __.not_(__.inV().has('v',0)))).project("role", "end").by(__.label()).by(__.inV()).toList()

    label= g.V(o.id).out("instanceOf").label().next()
    for edge in check:
        card = g.V(edge['end'].id).out("instanceOf").out("associations").has("role", edge['role']).where(__.out("targetType").hasLabel(label)).values("cardinality_begin").next()
        #from o to edge['end'] via edge['role'] has cardinality card
        x = card.split(".")
        if(len(x) > 1):
            begin = x[0]
            end = x[1]
        else:
            begin = x[0]
        print(begin)




    print(g.V(o.id).outE().inV().where(__.out("instanceOf").out("instanceOf").hasLabel("assets")).toList())
    print(g.V(o.id).properties().toList())
    print(g.V(o.id).bothE().where(__.otherV().out("instanceOf").out("instanceOf").hasLabel("assets")).properties().toList())
 
    

    