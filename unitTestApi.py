from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
from graph_api import *
# g should refer to an data base that is initiated 
# with at least the MAL and DSL layers (coreLang 0.2.0)

def testAddObject(g):
    ############
    # Scenario 1 : Add a new object that exits in the DSL layer (coreLang 0.2.0)
    ############
    id1 = addNewObject(g, "Identity", "id1")
    #Check that the object exits
    assert g.V(id1.id).hasNext()
    #Check that the object is connected to the Identity vertex in the DSL layer
    assert g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel("Identity").in_("instanceOf").hasId(id1.id).hasNext()
    # Check that all attack steps is connected to the object
    aSteps = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel("Identity").out("attackSteps").toList()
    nrOfASteps = len(aSteps)
    assert g.V(id1.id).out("attackStep").count().next() == nrOfASteps
    # Check that all defenses is connected to the object
    defenses = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel("Identity").out("defenses").toList()
    nrOfdefenses = len(defenses)
    assert g.V(id1.id).out("defense").count().next() == nrOfdefenses
    #The object should have a property that states v = 1
    v = g.V(id1.id).values("v").toList()
    assert v[0] == 1

    ###############
    # Scenario 2 : Addning a object whoms metaConcept does not exits in the DSL layer
    ###############
    o = addNewObject(g, "nonExiting", "o1")
    #should return an empty list (and print that the object is not in the DSL layer)
    assert o == []
    #make sure that there is no object called o1
    o1Exits = g.V().has('name', "o1").hasNext()
    assert o1Exits == False

    ###################
    # Scenario 3 : Adding an object whoms metaConcept is abstract
    ###################
    abstractObject = addNewObject(g, "Object", "abstract1")
    #Should not be possible and return an empty list (and print that the object class is abstract)
    assert abstractObject == []
    #make sure that there is no object called abstract1
    oExits = g.V().has('name', "abstract1").hasNext()
    assert oExits == False

    ##################
    # Scenario 4: Adding an object that extends another object
    ##################
    rf = addNewObject(g, "RoutingFirewall", "rf1")

    #The object should be added in the instance layer
    assert g.V(rf.id).hasNext()
    #The object should have an instanceOf edge to the asset in the DSL layer
    assert g.V(rf.id).out("instanceOf").hasLabel("RoutingFirewall").hasNext()

