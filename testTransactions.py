from gremlin_python import statics
from gremlin_python.structure.graph import Graph
from gremlin_python.process.graph_traversal import __
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection

if __name__ == "__main__":
    graph = Graph()
    connection = DriverRemoteConnection('ws://localhost:8182/gremlin', 'g')
    # The connection should be closed on shut down to close open connections with connection.close()
    g = graph.traversal().withRemote(connection)
    g.V().drop().iterate()
    # Reuse 'g' across the application

    h = g.addV("Hello").next()
    y = g.addV("You").next()
    e = g.V(h.id).addE("to").to(y).next()
    print(g.V().hasLabel("Hello").toList())
    print(g.E(e.id).toList())
    #graph.tx().commit() #commiting transaction
    #graph.tx().rollback() #Rollback transaction
    #print(g.V().hasLabel("Hello").toList())