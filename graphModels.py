from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.traversal import Cardinality, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
import scad
import requests
import csv
import json
import re
from os import getcwd

def drop_all(g):
    # Delete all vertices
    g.V().drop().iterate()

###########  MAL layer ##############
def mal(g):
    # Add the root asset which is a starting point for schemantic queries
    root = g.addV("root").next()
    # Add the main building blocks of MAL
    assets = g.addV("assets").next()
    attackSteps = g.addV("attackSteps").next()
    defenses = g.addV("defenses").next()
    associations = g.addV("associations").next()
    # Add root edges
    g.V(root.id).addE("attackSteps").to(attackSteps).iterate()
    g.V(root.id).addE("assets").to(assets).iterate()
    g.V(root.id).addE("defenses").to(defenses).iterate()
    g.V(root.id).addE("associations").to(associations).iterate()

    #### Add DSL and instance properties ####

    #DSL properties for attack steps
    a_type = g.addV("type").next()
    g.V(attackSteps.id).addE("DSLProperties").to(a_type).iterate()

    #Instance properties for attack steps
    ttc5 = g.addV("TTC-5%").next()
    ttc50 = g.addV("TTC-50%").next()
    ttc95 = g.addV("TTC-95%").next()

    g.V(attackSteps.id).addE("instanceProperties").to(ttc5).iterate()
    g.V(attackSteps.id).addE("instanceProperties").to(ttc50).iterate()
    g.V(attackSteps.id).addE("instanceProperties").to(ttc95).iterate()

    #DSL Porperties for associations
    role = g.addV("role").next()
    cardi_begin = g.addV("carinality_begin").next()
    g.V(associations.id).addE("DSLProperties").to(role).iterate()
    g.V(associations.id).addE("DSLProperties").to(cardi_begin).iterate()

    #Instance Properties for assets
    tag = g.addV("tag").next()
    name = g.addV("name").next()
    g.V(assets.id).addE("instanceProperties").to(tag).iterate()
    g.V(assets.id).addE("instanceProperties").to(name).iterate()

    #Instance properties for defenses
    active = g.addV("active").next()
    g.V(defenses.id).addE("instanceProperties").to(active).iterate()


def readMALSpec():
    #url = "https://raw.githubusercontent.com/mal-lang/coreLang/master/src/main/mal/coreLang.mal"
    url = "https://raw.githubusercontent.com/mal-lang/coreLang/master/src/main/mal/coreLang.mal"
    directory = getcwd()

    filename = 'mal.txt'
    r = requests.get(url)
    
    f = open(filename,'w')
    f.write(r.text)
    f.close()

    with open(filename) as infile, open('output.txt', 'w') as outfile:
        for line in infile:
            if not line.strip(): continue  # skip the empty line
            outfile.write(line)  # non-empty line. Write it to output

    spec  = open('output.txt', "r") 
    content = spec.readlines()
    asso = False
    assocs = []
    assets = []
    currentAsset = {"name": "", "attackSteps":[], "defenses": []}

    for line in content:
        words = line.split()
        if(asso == False):
            if(len(words) >= 2):
                if(words[0] == "asset"):
                    if(currentAsset["name"] != ""):
                        assets.append(currentAsset)
                        currentAsset = {"name": "", "attackSteps":[], "defenses": []}
                    currentAsset["name"] = words[1]
                    ## Create a new asset
                if(words[1] == "asset"):
                    if(currentAsset["name"] != ""):
                        assets.append(currentAsset)
                        currentAsset = {"name": "", "attackSteps":[], "defenses": []}
                        
                    currentAsset["name"] = words[2]
                
                #All defnses and attack steps until a new asset is 
                # present belongs to the prev asset

                if(words[0] == "|"): #Attack step of type OR
                    currentAsset["attackSteps"].append({"name": words[1], "type": "OR"})
                if(words[0] == "&"): #Attack step of type AND
                    currentAsset["attackSteps"].append({"name": words[1], "type": "AND"})
                if(words[0] == "#"): #Defense
                    currentAsset["defenses"].append({"name": words[1]})
                #spec.close()

                ## no more assets, just associations
                if(words[0] == "associations"):
                    asso = True
                    assets.append(currentAsset)
                
        else:
            if(len(words) >= 2):
                for d in assets:
                    
                    if(d["name"] == words[0]):
                        line = ''.join(words)
                        lineContent = re.split('\[|\]|<--|-->', line)
                        # print(lineContent)
                        
                        assoc = {}
                        # if(len(words) == 8):
                        #     fix = words[6].split("[")
                        #     card = fix[0]
                        #     role = '[' + fix[1]
                        #     asset2 = words[7]
                        # else:
                        #     card = words[6]
                        #     role = words[7]
                        #     asset2 = words[8]

                        # assoc["linkName"] = words[4]
                        # assoc["asset1"] = words[0]
                        # assoc["asset2"] = asset2
                        # chars = "[]"
                        # for c in chars:
                        #     words[1].replace(c, '')
                        #     words[7].replace(c, '')
                        # assoc["role1"] = words[1]
                        # assoc["role2"] = role
                        
                        # assoc["cardinality1"] = words[2]
        
                        # assoc["cardinality2"] = card

                        assoc["linkName"] = lineContent[3]
                        assoc["asset1"] = lineContent[0]
                        assoc["asset2"] = lineContent[6]
                        assoc["role1"] = lineContent[1]
                        assoc["role2"] = lineContent[5]
                        assoc["cardinality1"] = lineContent[2]
                        assoc["cardinality2"] = lineContent[4]
                        #print(assoc["cardinality1"], assoc["cardinality2"])
                        assocs.append(assoc)
                        break
    print(len(assocs))      
    return assets, assocs

########### DSL Layer ###############

#Adds an assets in the DSL layer
def addAssets(g, assets):
    for asset in assets:
        #create the asset with the name as label
        a = g.addV(asset["name"]).next()
        #The asset is an instance of the asset node in the MAL layer
        g.V(a.id).addE("instanceOf").to(g.V().hasLabel("root").out("assets")).iterate()
        #Add defenses
        addDefenses(g, a, asset["defenses"])
        #Add attack steps
        addAttackSteps(g, a, asset["attackSteps"])


def addAssociations(g, assocs):
    for a in assocs:
        role1 = a['role1'].strip("[]")
        role2 = a['role2'].strip("[]")
        #add two new assocs vertices containing information about both sides
        a1 = g.addV(a["linkName"]).property("role", role1).property("cardinality_begin", a["cardinality1"]).next()
        a2 = g.addV(a["linkName"]).property("role", role2).property("cardinality_begin", a["cardinality2"]).next()

        #add instanceOf edges to associations in the MAL Layer
        g.V(a1.id).addE("instanceOf").to(g.V().hasLabel("root").out("associations")).iterate()
        g.V(a2.id).addE("instanceOf").to(g.V().hasLabel("root").out("associations")).iterate()
        #Add association edges from the asset to its role and target edges
        g.V().hasLabel(a["asset1"]).addE("associations").to(a1).iterate()
        g.V().hasLabel(a["asset2"]).addE("associations").to(a2).iterate()

        g.V(a1.id).addE("targetType").to(g.V().hasLabel(a["asset2"])).iterate()
        g.V(a2.id).addE("targetType").to(g.V().hasLabel(a["asset1"])).iterate()

# Adds defenses to an asset in DSL layer
def addDefenses(g, asset, defenses): 
    # g : Graph traversal source to access the database
    # asset : is a vertex in the DSL layer representing 
    # the asset the defenses should relate to
    #
    # defenses : list of dictionaries {"name" : "nameOfDefense"}
    for defense in defenses:
        #Add a new vertex representing the defense
        d = g.addV(defense["name"]).next()
        #Add an edge (defense relation) from the asset having the defense
        g.V(asset.id).addE("defenses").to(d).iterate()

# Adds attack steps to an asset on the DSL layer   
def addAttackSteps(g, asset, attackSteps):
# g : Graph traversal source to access the database
# asset : is a vertex in the DSL layer representing 
# the asset the defenses should relate to
#
# attackSteps : list of dictionaries {"name" : "nameOfAttackStep", "type": "type"}
    for step in attackSteps:
        a = g.addV(step["name"]).property("type", step["type"]).next()
        g.V(a.id).addE("instanceOf").to(g.V().hasLabel("root").out("attackSteps")).iterate()
        g.V(asset.id).addE("attackSteps").to(a).iterate()


###################### Instance Layer #############################
def readCSV(file):    
    # initializing the titles and rows list
    fields = []
    rows = []
    headerInfo = []
    
    # reading csv file
    with open(file, 'r') as csvfile:
        # creating a csv reader object
        csvreader = csv.reader(csvfile)
        
        # extracting field names through first row
        headerInfo.append(next(csvreader))
        headerInfo.append(next(csvreader))
        headerInfo.append(next(csvreader))
        headerInfo.append(next(csvreader))
        fields = next(csvreader)
    
        # extracting each data row one by one
        for row in csvreader:
            rows.append(row)

        return rows
    
    
#Add attack steps with TTC values and set active defenses
def getActiveDefenses(file, oid, metaConcept):
    assets = scad.open(file)
    #Get the meta concept 
    activeDefenses = []
    for o in assets['eom_etree'].findall('objects'):
        if (o.get('id') == oid):
            for evidence in o.findall('evidenceAttributes'):
                if evidence.findall('evidenceDistribution'):
                    defense = evidence.get("metaConcept")[0].lower() + evidence.get("metaConcept")[1:]
                    #might fix to  handle probability, on, off etc
                    activeDefenses.append(defense)        
    return activeDefenses

def addInstanceDefenses(g, vertex, oid, metaConcept, file):
    #get the defenses in the DSL layer associated to the object type
    defenses = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).out("defenses").project("id", "label").by(T.id).by(T.label).toList()
    activeDefenses = getActiveDefenses(file, oid, metaConcept)
    for defense in defenses:
        # check if the defense is active in the oem file
        if(defense['label'] in activeDefenses):
            #create an active defense vertex
            d = g.addV().property('active', 1).next()
            #The instance object has an edge to the defense
            g.V(vertex.id).addE("defense").to(d).iterate()
            #The defense is an instance of a defence in the DSL layer
            g.V(d.id).addE("instanceOf").to(g.V(defense['id'])).iterate()
        else:
            #create an inactive defense vertex
            d = g.addV().property('active', 0).next()
            #The instance object has an edge to the defense
            g.V(vertex.id).addE("defense").to(d).iterate()
            #The defense is an instance of a defence in the DSL layer
            g.V(d.id).addE("instanceOf").to(g.V(defense['id'])).iterate()

# Gets the TTC value for an attack step, if there is none return 0
def getTTC(oid, name, attackStep, simulation):
    #TTC values is on index 6,7,8 and id of the object id is on index 1
    #and the name of the attack step is on index 5
    #print(name, attackStep)
    for row in simulation:
       
        if((row[1] == oid) and (row[5].lower() == attackStep.lower())):
            return row[6], row[7], row[8]
    return 0, 0, 0

def addInstanceAttackSteps(g, vertex, metaConcept, oid , name , simulation):
    #for each attack step get the TTC values from the simulation and create the
    #attack step vertex

    #get the attack steps from the DSL layer as a list
    attackSteps = g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(metaConcept).out("attackSteps").project("id", "label").by(T.id).by(T.label).toList()
    for attackStep in attackSteps:
        TTC5, TTC50, TTC95 = getTTC(oid, name, attackStep['label'], simulation)
        #Add the attack step as a vertex in the instance layer with the ttc values
        aStep = g.addV().property('TTC-5%', TTC5).property('TTC-50%', TTC50).property('TTC-95%', TTC95).next()
        #connect to the model
        #add an edge between the object and the attack step
        g.V(vertex.id).addE("attackStep").to(aStep).next()
        #the attack step is an instance of the attack step in the DSL layer
        g.V(aStep.id).addE("instanceOf").to(g.V(attackStep['id'])).iterate()

def xmlToModel(g, file, csv):
    eom = scad.open(file)
    assets = scad.get_assets(eom)
    simulation = readCSV(csv)
    
    for o in assets['objects']:
        if(not (o['metaConcept'] == 'Attacker')):
            #add the instance object, need to keep the securiCAD id for the associations
            vertex = g.addV().property('name', o['name']).property('id', o['id']).next()
            #Check if there is any tags present
            if('attributesJsonString' in o):
                for k, v in json.loads(o['attributesJsonString']).items():
                    g.V(vertex.id).property(k,v).next()
                
            #the object vertex is an instance of a DSL asset
            g.V(vertex.id).addE("instanceOf").to(g.V().hasLabel("root").out("assets").in_("instanceOf").hasLabel(o['metaConcept'])).iterate()

            addInstanceAttackSteps(g, vertex, o['metaConcept'], o['exportedId'], o['name'] , simulation)
            addInstanceDefenses(g, vertex, o['id'], o['metaConcept'], file)
        
    #assumes that associations in the instance model is correct in respect to the DSL
    for a in assets['assocs']:
        if( '.attacker' not in a['targetProperty'] ):
            #getLinkName(g.V().has('id', a['sourceObject']), a['targetProperty'], a['sourceProperty'])
            g.V().has('id', a['sourceObject']).addE(a['sourceProperty']).to(g.V().has('id', a['targetObject'])).iterate()
            g.V().has('id', a['targetObject']).addE(a['targetProperty']).to(g.V().has('id', a['sourceObject'])).iterate()
    return eom
def addVertex(g, className, name, defenses): 
    #Need to check rules in the MAL language
    return g.addV(className)
def addEdge(g, associationName, fromAssetId, toAssetId):
    return g.addE(associationName)
    
#Creation of the example graph provided in Chapter. 2 representing a band.
def exampleModel(g):
    #drop the old graph
    drop_all(g)
    #Creation of all the vertecies
    johan = g.addV("Person").property("Name", "Johan").property("Gender", "Male").next()
    noomi = g.addV("Person").property("Name", "Noomi").property("Gender", "Female").next()
    band = g.addV("Band").property("Name", "Soulmates").property("Genre", "Indie").property("Founded", "2019").next()
    piano = g.addV("Instrument").property("Type", "Piano").next()
    guitar = g.addV("Instrument").property("Type", "Guitar").next()
    festival = g.addV("Festival").property("Location", "Stockholm").next()

    #Creation of all the edges
    g.addE("member").property("weight", 0.5).from_(johan).to(band).iterate()
    g.addE("member").property("weight", 0.5).from_(noomi).to(band).iterate()
    g.addE("plays").property("weight", 0.8).from_(johan).to(piano).iterate()
    g.addE("plays").property("weight", 0.5).from_(noomi).to(guitar).iterate() 
    g.addE("played_at").property("weight", 0.8).from_(band).to(festival).iterate()   
        
    

