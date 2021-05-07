from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import Cardinality, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
import matplotlib.pyplot as plt
import networkx as nx

def drawInstanceLevel(g):
    #all edges between two objects
    e = g.E().where(__.and_(__.inV().out("instanceOf").out("instanceOf").hasLabel("assets"),\
                        __.outV().out("instanceOf").out("instanceOf").hasLabel("assets"))).toList()
    edges = []
    for edge in e:
        elem = {}
        elem['role'] = g.E(edge.id).label().next()
        fr = g.E(edge.id).outV().project("name", "id").by(__.values("name")).by(__.id()).toList()
        to = g.E(edge.id).inV().project("name", "id").by(__.values("name")).by(__.id()).toList()
        elem['from'] = fr[0]['name'] + str(fr[0]['id'])
        elem['to'] = to[0]['name'] + str(to[0]['id'])
        edges.append(elem)
    
    
    k = []
    for i in edges:
        h = [i['from'], i['to']]
        k.append(h)
    
    G = nx.MultiDiGraph()
    G.add_edges_from(k)
    pos = nx.spring_layout(G)
    plt.figure()    
    nx.draw(G,pos,edge_color='black',width=1,linewidths=1,\
    node_size=500,node_color='pink',alpha=0.9,\
    labels={node:node for node in G.nodes()})
    nx.draw_networkx_edge_labels(G,pos,edge_labels={(elem['from'],elem['to']):elem['role'] for elem in edges},font_color='red')
    plt.axis('off')
    plt.show()