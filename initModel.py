from gremlin_python import statics
from gremlin_python.structure.graph import Graph
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import P, T
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from graphModels import xmlToModel, mal, addAssets, readMALSpec, drop_all, addAssociations

if __name__ == "__main__":
    g = traversal().withRemote(DriverRemoteConnection('ws://localhost:8182/gremlin', 'g'))
    drop_all(g)
    #MAL layer
    mal(g)
    #DSL layer
    assets, assocs = readMALSpec()
    addAssets(g, assets)
    addAssociations(g, assocs)
    #instance layer
    xmlToModel(g, './data-models/example1.sCAD', './data-models/example1.csv')
    #xmlToModel(g, './data-models/apivalidation.sCAD', './data-models/apivalidation.csv')

    