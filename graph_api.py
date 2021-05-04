from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
import networkx as nx
#import matplotlib.pyplot as plt
########## Api to change the Instance layer in the data model ##########
# Public functions: 
# addObject, validatedAddObject, 

def addNewObject(g, metaConcept, name):
    #find the meta asset
    metaA = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).next()
    #Get attack steps from the meta asset
    aSteps = g.V(metaA.id).out("attackSteps").toList() #[v[1], v[2], .., v[n]]
    #Get defenses from the meta asset
    defenses = g.V(metaA.id).out("defenses").toList()
    #create the inctance object
    obj =  g.addV().property('name', name).property('v', 1).next()
    #add edge to the meta asset
    g.V(obj.id).addE("instanceOf").to(metaA).iterate()

    #add instance attackStep (a is a graph traversal object)
    for a in aSteps:
        #create instance attack step
        step = addInstanceAttackStep(g)
        #add an instanceOf edge between the meta attack step and the instance
        g.V(step.id).addE("instanceOf").to(a).iterate()
        #add an attackStep edge from the instance object to the instance attack step
        g.V(obj.id).addE("attackStep").to(step).iterate()

    #add instance defense
    for d in defenses:
        #create the instance defense
        defense = addInstanceDefense(g)
        #add an instanceOf edge between the meta defense and the instance
        g.V(defense.id).addE("instanceOf").to(d).iterate()
         #add an defense edge from the instance object to the instance defense
        g.V(obj.id).addE("defense").to(defense).iterate()
    
    print("added object...")
    return obj

def addNewAssociation(g, obj1, obj2, linkName):
    metaConceptObj1 = g.V(obj1.id).out("instanceOf").label().next()
    metaConceptObj2 = g.V(obj2.id).out("instanceOf").label().next()
       
    assocs = g.V().hasLabel("root").out("associations").in_("instanceOf").hasLabel(linkName).\
            where(__.or_(__.and_(\
                        __.in_("associations").hasLabel(metaConceptObj1),\
                        __.out("targetType").hasLabel(metaConceptObj2))\
                        ,\
                        __.and_(\
                        __.in_("associations").hasLabel(metaConceptObj2),\
                        __.out("targetType").hasLabel(metaConceptObj1)))).toList()                            
    
    #check that both metaConcepts are a member of the link
    valid = True
    for asset in assocs:
        target = g.V(asset.id).out("targetType").label().next()
        start = g.V(asset.id).in_("associations").label().next()
        if not ((target == metaConceptObj1 or start == metaConceptObj1) and (target == metaConceptObj2 or start == metaConceptObj2)):
            valid = False
    
    if(valid):
        roleAndCardObj1 = g.V(obj1.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
        roleAndCardObj2 = g.V(obj2.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
        #Add edges named after the roles (with a v = 1 to indacate a new change)
        g.V(obj1.id).addE(roleAndCardObj2["role"]).property('v', 1).to(g.V(obj2.id)).iterate()
        g.V(obj2.id).addE(roleAndCardObj1["role"]).property('v', 1).to(g.V(obj1.id)).iterate()
#TO DO#
#Removing an object means that all edges connected to that object will be removed
def removeObject(g, obj):
    #Set the object to 0
    g.V(obj.id).property('v', 0).next()
    #Set all edges from the object 0
    g.V(obj.id).bothE().where(__.otherV().out("instanceOf").out("instanceOf").hasLabel("assets")).property('v', 0).next()
def removeAssociation(g, edge1, edge2):
    #tag the edges with 0
    g.E(edge1.id).property('v', 0).next()
    g.E(edge2.id).property('v', 0).next()

## The model is assumed to be correct outside the pattern
# Validations on new object menas validating that object and its neigbouring objects
# since the carinalities for thos can be affected
# VALIDATION on new assocs validates the objects connecting through the assoc
#all validations does not take account for 0:s
def validatePatternExchange(g):
    # Need to look for 1:s (added objects and assocs)
    #Validate the cardinalites, of that object and its neigbouring objects
    #that is not taged with a 0
    newObejcts = g.V().has('v', 1).toList()
    for obj in newObejcts:
        #Get the neigbours
        neighbours = g.V(obj.id).outE().not_(__.has('v', 0)).inV().where(__.out("instanceOf").out("instanceOf").hasLabel("assets")).toList()
        validateObject(g, obj) #Validate the newly added object
        for n in neighbours:
            validateObject(g, n) #Validate the neighbours of the new object
    #For assocs validate the objects the edge connects
    #that all objects are connected to a meta assets
    newAssociations = g.E().has('v', 1).toList()


#Validate all associations to that object and that it has a meta asset in the DSL Layer
#The validations ignores 0:s
#def validateObject(g, obj):
    #check that the object has an associated asset in the DSL layer


#Make sure that the other direction is present aswell
#def validateAssociation(g, edge):

#removeValidatedPattern():
    #If validatePattern() == True
        #remove(0)
        #deleteVProperty(0)
    #else
        #remove(1)
        #deleteVProperty(1)


# Validate if the object can be added in the model involves 
# 1. checking the DSL layer that the asset exists that the object is an instance of
def validatedAddObject(g, metaConcept):
    assetExists = False
    asset = g.V("root").out("assets").in_("instanceOf").hasLabel(metaConcept).toList()
    if(asset):
        #asset exists in the DSL layer
        assetExists = True
    return assetExists
    
# Needs to validate before calling
def addObject(g, name, metaConcept, tag = None):
    # g Graph traversal source
    # name  name of the instance object
    # metaConcept   name of the DSL asset
    # tag {key1 : val1, key2: val2, ...}

    #find the meta asset
    metaA = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).next()
    #Get attack steps from the meta asset
    aSteps = g.V(metaA.id).out("attackSteps").toList() #[v[1], v[2], .., v[n]]
    #Get defenses from the meta asset
    defenses = g.V(metaA.id).out("defenses").toList()
    #create the inctance object
    obj =  g.addV().property('name', name).next()
    #add edge to the meta asset
    g.V(obj.id).addE("instanceOf").to(metaA).iterate()
    if(tag):
        for k,v in tag.items():
            g.V(obj.id).property(k, v).next()
    

    #add instance attackStep (a is a graph traversal object)
    for a in aSteps:
        #create instance attack step
        step = addInstanceAttackStep(g)
        #add an instanceOf edge between the meta attack step and the instance
        g.V(step.id).addE("instanceOf").to(a).iterate()
        #add an attackStep edge from the instance object to the instance attack step
        g.V(obj.id).addE("attackStep").to(step).iterate()

    #add instance defense
    for d in defenses:
        #create the instance defense
        defense = addInstanceDefense(g)
        #add an instanceOf edge between the meta defense and the instance
        g.V(defense.id).addE("instanceOf").to(d).iterate()
         #add an defense edge from the instance object to the instance defense
        g.V(obj.id).addE("defense").to(defense).iterate()
    print("added object...")
    #return obj, and bool if it is succefull
    return obj


#creates a new attack step vertex in the instance layer. 
# Adds 0 as a default value to new attack steps
def addInstanceAttackStep(g):
    return g.addV().property("TTC-5%", 0).property("TTC-50%", 0).property("TTC-95%", 0).next()

#creates a new defense vertex in the instance layer
#the default values is 0 for the active property
def addInstanceDefense(g):
    return g.addV().property("active", 0).next()

#Activate a defense if it exits
def activateDefense(g, obj, defense):
    g.V(obj.id).out("defense").where(__.out("instanceOf").hasLabel(defense)).property("active", 1).next()

#deactivate a defense if it exits
def deactivateDefense(g, obj, defense):
    g.V(obj.id).out("defense").where(__.out("instanceOf").hasLabel(defense)).property("active", 0).next()

#adds a tag key value pair as a property to an object 
def addTag(g, obj, tag):
# g graph traversal source
# obj the vertex that should include the tag
# tag {key, val}
    for k, v in tag.items():
        g.V(obj.id).property(k,v).next()

def removeTag(g, obj, tag):
    for k, v in tag.items():
        g.V(obj.id).properties(k).drop()

def setTTC(g, obj, attackStep, ttc):
# g graph traversal source
# obj the vertex that has the attack step
# attackStep the name of the attack step
# ttc {'TTC-5%' : value, 'TTC-50%': value, 'TTC-95%' : value}
    g.V(obj.id).out("attackStep").\
        where(__.out("instanceOf").hasLabel(attackStep)).\
        property("TTC-5%", ttc["TTC-5%"]).\
        property("TTC-50%", ttc["TTC-50%"]).\
        property("TTC-95%", ttc["TTC-95%"]).next()

# removing an object removes all edges in and out of the object. 
# All associated defenses and attack steps is removed as well
# This could potentially lead to disconected components in the graph
def removeObject(g, obj):
    g.V(obj.id).out("defense").drop()
    g.V(obj.id).out("attackStep").drop()
    g.V(obj.id).drop()

#Check that there exits an assoc with the provided link name between obj1 and obj2
# in both directions
# Check that the caridnality validates to the model
#def validateAddAssociation(g, obj1, obj2, linkName):
def addAssociation(g, obj1, obj2, linkName):
    roleAndCardObj1 = g.V(obj1.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
    roleAndCardObj2 = g.V(obj2.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
    print("TESTING", roleAndCardObj1)
    validate = True
    if(validate):
        metaConceptObj1 = g.V(obj1.id).out("instanceOf").label().next()
        metaConceptObj2 = g.V(obj2.id).out("instanceOf").label().next()
        #Find the link name between the objects
        
        assocs = g.V().hasLabel("root").out("associations").in_("instanceOf").hasLabel(linkName).toList()
        #check that both metaConcepts are a member of the link
        valid = True
        for asset in assocs:
            target = g.V(asset.id).out("targetType").label().next()
            start = g.V(asset.id).in_("associations").label().next()
            if not ((target == metaConceptObj1 or start == metaConceptObj1) and (target == metaConceptObj2 or start == metaConceptObj2)):
                valid = False
        #Check cardinalites
        doChanges = True
        if(valid):
            if(roleAndCardObj1["card"] == "0..1"):
                #Then obj2 can not have other edges to the same type of asset as 
                #obj1
                if(g.V(obj1.id).out().where(__.out("instanceOf").hasLabel(metaConceptObj2)).count().next() > 0):
                    doChange = False
            if(roleAndCardObj2["card"] == "0..1"):
                #Then obj1 can not have other edges to the same type of asset as 
                #obj2
                if(g.V(obj2.id).out().where(__.out("instanceOf").hasLabel(metaConceptObj1)).count().next() > 0):
                    doChange = False
        if(doChanges):
            print("Creating edges...")
            g.V(obj1.id).addE(roleAndCardObj1["role"]).to(g.V(obj2.id)).iterate()
            g.V(obj2.id).addE(roleAndCardObj2["role"]).to(g.V(obj1.id)).iterate()

#def removeAssociation(g, obj1, obj2, linkName):
    
def printModel(g):
    objects = g.V("root").out("assets").in_("instanceOf").in_("instanceOf").toList()

# def printInstanceModel(g):
#     G = nx.DiGraph()
#     G.add_edges_from([(1, 1), (1, 7), (2, 1), (2, 2), (2, 3), 
#                   (2, 6), (3, 5), (4, 3), (5, 4), (5, 8),
#                   (5, 9), (6, 4), (7, 2), (7, 6), (8, 7)])
  
#     plt.figure(figsize =(9, 9))
#     nx.draw_networkx(G, with_label = True, node_color ='green')




    
