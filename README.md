# thesis-work

## preliminaries
- Python
- Pip
- Gremlin server 
- SecuriCAD

## How to use the application
1. Start the gremlin server using `bin/gremlin-server.sh conf/gremlin-server-modern-py.yaml` on mac or `bin/gremlin-server.bat conf/gremlin-server-modern-py.yaml` on windows
2. In the `patternMatching.py` file the main method is the entry point of the application. The variables called `URL1`, `URL2` etc is where you specify the specific DSL you want to use for example coreLang, link the meta-page from github. These will later be added to the graph database one by one.
3. The function `xmlToModel()` takes a XML and a CSV files as input, this function converts the SecuriCAD model togheter with the simulation results to the instance-layer in the database.
4. The function `runTest()`runs the predefinded exchange patterns on the model which are located in the file `tests.py`.
5. The function `convertPropertyGraphToSecuriCAD()`takes the reference to the database and to the xml file and rewrites the xml file with the new updated model.
