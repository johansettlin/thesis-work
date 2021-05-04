rules = 
    {
        "classes":{
            "Credential": {
                "className": "name",
                "metaConcept": "Credential"
                "id": "number"
                "attackSteps": ["x","y"],
                "defenses": ["z","j"]
            }
        },
        "associations":{
            "SysExecution": {
                "System": {
                    "role": "hostSystem",
                    "cardinality": "0..1"
                },
                "Application": {
                    "role": "sysExecutedApps",
                    "cardinality": "*"
                }
                
            },
      
        }
        
    }