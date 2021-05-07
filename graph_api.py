from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
import networkx as nx
#import matplotlib.pyplot as plt
########## Api to change the Instance layer in the data model ##########
# Public functions: 
# addObject, validatedAddObject, 

### Structural API ###
def addNewObject(g, metaConcept, name):
    #find the meta asset
    if( not g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).hasNext()):
        # The metaAsset does not exits
        return []
    metaA = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).next()
    if(metaA):
        #Get attack steps from the meta asset
        aSteps = g.V(metaA.id).out("attackSteps").toList() 
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
        
        #print("added object...")
        return obj
    else:
        return []

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
            print("The association does not exits")
            valid = False
    
    if(valid):
        roleAndCardObj1 = g.V(obj1.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
        roleAndCardObj2 = g.V(obj2.id).out("instanceOf").out("associations").hasLabel(linkName).project("role", "card").by("role").by("cardinality_begin").next()
        #Add edges named after the roles (with a v = 1 to indacate a new change)
        #check that the assoc does not already exists
        if (g.V(obj1.id).out(roleAndCardObj2["role"]).hasId(obj2.id).hasNext()):
            #Already exits
            print("Trying to add an exitsting association between two objects")
            return False
        g.V(obj1.id).addE(roleAndCardObj2["role"]).property('v', 1).to(g.V(obj2.id)).iterate()
        g.V(obj2.id).addE(roleAndCardObj1["role"]).property('v', 1).to(g.V(obj1.id)).iterate()
    return valid

#Removing an object means that all edges connected to that object will be removed
def removeObject(g, obj):
    #Make sure that the object exits
    if (not g.V(obj.id).hasNext()):
        print("Tried to remove an non-existing object")
        return 
    #Set the object to 0
    g.V(obj.id).property('v', 0).next()
    #Set all edges from the object 0
    g.V(obj.id).bothE().where(__.otherV().out("instanceOf").out("instanceOf").hasLabel("assets")).property('v', 0).next()
#The role of obj2 is needed obj -> obj2
def removeAssociation(g, obj1, obj2, role2):
    #Check that the association exits
    if(not g.V(obj1.id).out(role2).hasId(obj2.id).hasNext()):
        #does not exits
        print("trying to removed an non-exitsting association")
        return
    #Find the role in the oposite direction
    #Get the link name
    link = getLinkName(g, obj1, obj2, role2)
    

    role1 = g.V(obj1.id).out("instanceOf").out("associations")\
                .where(__.and_(__.hasLabel(link),\
                              __.out("targetType").hasLabel(g.V(obj2.id).out("instanceOf").label().next()))\
                ).values("role")\
                .next()
    
    #tag the edges with 0
    g.V(obj1.id).outE(role2).where(__.inV().hasId(obj2.id)).property('v', 0).next()
    g.V(obj2.id).outE(role1).where(__.inV().hasId(obj1.id)).property('v', 0).next()

### Validation on structural changes ###
## The model is assumed to be correct outside the pattern
# Validations on new object menas validating that object and its neigbouring objects
# since the carinalities for thos can be affected
# VALIDATION on new assocs validates the objects connecting through the assoc
#all validations does not take account for 0:s
def validatePatternExchange(g):
    # Need to look for 1:s (added objects and assocs)
    #Validate the cardinalites, of that object and its neigbouring objects
    #that is not taged with a 0
    newObejcts = g.V().has('v', 1).toList() #Need a full validation 
    newAssocs = g.E().has('v', 1).toList() #Validate only that assoc for the objects
    removedAssocs = g.E().has('v', 0).toList()  #Validate only that assoc for the objects
    valid = True
    #Validate all new objects
    for obj in newObejcts:
        if(valid):
            valid = fullValidateObject(g, obj) #Validate the newly added object
    
    #Validate new assocs
    for assoc in newAssocs:
         if(valid):
            valid = validateAssoc(g, assoc)

    #Validate removed assocs (same check as for new assocs)
    for rAssoc in removedAssocs:
        if(valid):
            valid = validateAssoc(g, rAssoc)

    # If the pattern exchange is valid remove the 0:s from the model and keep the 1:s
    if(valid):
        print("change")
        for rAssoc in removedAssocs:
            g.E(rAssoc.id).drop().iterate()
        #permanently remove object with 0:s
        removedObjects = g.V().has('v', 0).toList()
        for o in removedObjects:
            deleteObject(g,o)

        #Drop all the properties with 1:s
        g.V().has('v', 1).properties('v').drop().iterate()
        g.E().has('v', 1).properties('v').drop().iterate()

    else: #Keep the 0:s and remove the 1:s
        print("restore")
        for assoc in newAssocs:
             g.E(assoc.id).drop().iterate()
        for o in newObejcts:
            deleteObject(g, o)
        
        #Drop all the properties with 0:s
        g.V().has('v', 0).properties('v').drop().iterate()
        g.E().has('v', 0).properties('v').drop().iterate()

def deleteObject(g, o):
    #delete all attackSteps and defenses
    g.V(o.id).out("defense").drop().iterate()
    g.V(o.id).out("attackStep").drop().iterate()

    #delete the object
    g.V(o.id).drop().iterate()

def validateAssoc(g, assoc):
    objToValidate = g.E(assoc.id).outV().next()
    meta1 = g.E(assoc.id).outV().out("instanceOf").label().next()
    meta2 = g.E(assoc.id).inV().out("instanceOf").label().next()
    role = g.E(assoc.id).label().next()
    card = g.E(assoc.id).\
            inV().\
            out("instanceOf").\
            out("associations").\
            has('role', role).\
            where(__.out("targetType").hasLabel(meta1)).\
            valueMap().next()
    #validate the assoc for meta 1 
    return validateOneAssocForObject(g, objToValidate, meta2, role, card['cardinality_begin'][0])
    


def fullValidateObject(g, o):
    #Get all the assocs out of the object in the language (DSL layer)
    valid = True
    metaAssocs = g.V(o.id).\
                match(__.as_("start").out("instanceOf").as_("metaStart"),\
                    __.as_("metaStart").in_("targetType").as_("assocInfo"),\
                    __.as_("assocInfo").in_("associations").as_("metaTarget")).\
                select("assocInfo", "metaTarget").by(__.valueMap()).by(__.label()).toList()
    for assoc in metaAssocs:
        if(valid):
            valid = validateOneAssocForObject(g, o , assoc['metaTarget'], assoc['assocInfo']['role'][0], assoc['assocInfo']['cardinality_begin'][0])
        else:
            return False
    return valid

def validateOneAssocForObject(g, o, targetMeta, role, card):
    #print(card)
    cardinality = card.split("..")
    
    #Set the upper and lowe bound for cardinalities
    if(len(cardinality) > 1):
        lowerBound = cardinality[0]
        upperBound = cardinality[1]
    else:
        lowerBound = cardinality[0]
        upperBound = True

    if(upperBound == "*"):
        upperBound = -1 #-1 = inf or *
    if(lowerBound == "*"):
        lowerBound = -1   
    #print("--", role, "--", lowerBound, "-meta-",targetMeta, "--", upperBound)
    #count go to all the objects connected through the role
    nrOfConnections = g.V(o.id).outE(role).\
                        not_(__.has('v',0)).\
                        where(__.and_(__.inV().out("instanceOf").hasLabel(targetMeta), \
                                        __.not_(__.inV().has('v',0)))).\
                        inV().count().next()

    #count the connections to the object matching the current association (without 0:s)
    #a fixed cardinlaity
    if(upperBound == True):
        if(nrOfConnections == int(lowerBound) or lowerBound == -1):
            #Valid
            return True
            
        else:
            #not valid
            print("1")
            return False
            
    #lower and upper bound
    else:
        if(upperBound == -1):
            #do not need to think about the max
            if(nrOfConnections >= int(lowerBound)):
                return True
            else:
                print("2")
                return False
        else:
            #need to be in the intervall between begin and end
            if((nrOfConnections >= int(lowerBound)) and (nrOfConnections <= int(upperBound))):
                return True
            else:
                print("3")
                return False
    


# Validate if the object can be added in the model involves 
# 1. checking the DSL layer that the asset exists that the object is an instance of
def validatedAddObject(g, metaConcept):
    assetExists = False
    asset = g.V("root").out("assets").in_("instanceOf").hasLabel(metaConcept).toList()
    if(asset):
        #asset exists in the DSL layer
        assetExists = True
    return assetExists
    
## Helper functions ###

#The role is the role of obj2
def getLinkName(g, obj1, obj2, role2):
    linkName = g.V(obj2.id).out("instanceOf").out("associations")\
        .where(__.and_(__.has("role", role2),\
                       __.out("targetType").hasLabel(g.V(obj1.id).out("instanceOf").label().next()))\
            )\
        .label()\
        .next()
    return linkName

#creates a new attack step vertex in the instance layer. 
# Adds 0 as a default value to new attack steps
def addInstanceAttackStep(g):
    return g.addV().property("TTC-5%", 0).property("TTC-50%", 0).property("TTC-95%", 0).next()

#creates a new defense vertex in the instance layer
#the default values is 0 for the active property
def addInstanceDefense(g):
    return g.addV().property("active", 0).next()

## API to change properties

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


## Functions to retrive information ##


def getRoleInAssociation(g, obj1, obj2):
    role = g.V(obj1.id).outE().where(__.inV().hasId(obj2.id)).label().next()
    return role


    
