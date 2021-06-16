#
#  Copyright (c) Foreseeti AB 2020
#
import getopt
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
import html


def open(file):
    """
    file: .sCAD filename
    Returns structure representing the open .sCAD file
    May throw a variety of exceptions for bad zip file, unexpected contents, bad XML etc.
    """
    zf = zipfile.ZipFile(file)
    basename = _validate_archive(zf)
    meta = json.loads(zf.read("meta.json"))
    eom_etree = ET.fromstring(zf.read(basename + ".eom").decode("utf-8"))
    cmx_etree = ET.fromstring(zf.read(basename + ".cmxCanvas").decode("utf-8"))
    
    return {'basename': basename, 'zip': zf, 'meta': meta, 'eom_etree': eom_etree, 'cmx_etree': cmx_etree}


def to_file(scad, file):
    """
    scad: scad structure as provided by open()
    file: filename for the .sCAD file to write
    Returns nothing
    May throw a variety of exceptions - scad data cannot be serialized, cannot write file etc.
    """
    with zipfile.ZipFile(file, "w", compression=zipfile.ZIP_DEFLATED) as ozf:
        ozf.comment = scad['zip'].comment
        ozf.writestr("meta.json", json.dumps(scad['meta']))
        ozf.writestr(scad['basename'] + ".cmxCanvas", ET.tostring(scad['cmx_etree'], encoding='utf8', method='xml'))
        ozf.writestr(scad['basename'] + ".eom", ET.tostring(scad['eom_etree'], encoding='utf8', method='xml'))


def get_assets(scad):
    """
    scad: scad structure as provided by open()
    Returns a dictionary with objects and association lists under keys 'objects' and 'assocs'
    Each list will in turn contain a dictionary containing the object/association attributes
    """
    objects = []
    for tag in scad['eom_etree'].findall('objects'):
        objects.append(tag.attrib)

    assocs = []
    for tag in scad['eom_etree'].findall('associations'):
        assocs.append(tag.attrib)

    ret = {}
    ret['objects'] = objects
    ret['assocs'] = assocs

    return ret


def set_meta(scad, langver=None, langname=None, langinfo=None):
    """
    Set the language metadata in the .sCAD file. None values are ignored and the existing value is kept.
    """
    if langver: scad['meta']['langVersion'] = langver
    if langname: scad['meta']['langID'] = langname
    if langinfo: scad['meta']['info'] = langinfo


def set_samples(scad, samples):
    """
    Set the # samples in the .sCAD file. None value is ignored and the existing value is kept.
    Use literal string 'default' to erase any sample setting in the model and rely on securiCAD default.
    """
    if samples:
        if samples == 'default':
            # delete attrib
            scad['eom_etree'].attrib.pop('samples', None)
        else:
            scad['eom_etree'].set('samples', samples)


def set_threshold(scad, threshold):
    """
    Set the threshold in the .sCAD file. None value is ignored and the existing value is kept.
    """
    if threshold:
        scad['eom_etree'].set('warningThreshold', threshold)


def rename_assets(scad, renspecs):
    """
    Rename assets in scad structure. renspecs is a list of tuples (<from asset>, <to asset>).
    """
    for r in renspecs:
        from_asset = r[0]
        to_asset = r[1]
        for tag in scad['eom_etree'].findall('objects'):
            if tag.get('metaConcept') == from_asset:
                tag.set('metaConcept', to_asset)
        for tag in scad['eom_etree'].findall('defenseDefaultValueConfigurations'):
            if tag.get('metaConcept') == from_asset:
                tag.set('metaConcept', to_asset)

    return


def rename_attacksteps(scad, renspecs):
    """
    Rename attacksteps in scad structure.
    renspec is a list of tuples (<asset name>, <from attackstep>, <to attackstep>).
    """
    for r in renspecs:
        asset = r[0]
        from_attackstep = r[1]
        to_attackstep = r[2]
        for tag in scad['eom_etree'].findall('objects'):
            if tag.get('metaConcept') == asset:
                for attackstep in tag.findall('evidenceAttributes'):
                    if attackstep.get('metaConcept') == from_attackstep:
                        attackstep.set('metaConcept', to_attackstep)

        # Handle attack steps to which the attacker is connected
        for assoc in scad['eom_etree'].findall("associations[@sourceProperty='firstSteps']"):
            tgtprop = assoc.get('targetProperty')
            m = re.fullmatch("(\w+)\.(\w+)", tgtprop)
            from_name = from_attackstep[0].lower() + from_attackstep[1:]
            to_name = to_attackstep[0].lower() + to_attackstep[1:]
            if m:
                if m.group(1) == from_name:
                    # Found attacker-connected attackstep named the same as the one to change.
                    # Need to verify that the attackstep belongs to an asset of the right type.
                    if scad['eom_etree'].find(f"objects[@id='{assoc.get('targetObject')}'][@metaConcept='{asset}']"):
                        # Yes, it was - change attacker-connected attackstep
                        assoc.set('targetProperty', f"{to_name}.{m.group(2)}")
                        # Now we also have to fix cmxCanvas in case there are views with the
                        # attacker connected to the attack steps
                        for view in scad['cmx_etree'].findall("view"):
                            findstr = ("viewConnection[@sourceProperty='firstSteps']"
                                       f"[@targetId='{assoc.get('targetObject')}']"
                                       f"[@targetProperty='{tgtprop}']")
                            viewconn = view.find(findstr)
                            if viewconn != None:
                                viewconn.set('targetProperty', f"{to_name}.{m.group(2)}")

    return


def rename_defenses(scad, renspecs):
    """
    Rename defenses (a list of tuples (<asset name>, <from defense>, <to defense>)) in eom (string).
    Returns the updated eom as a string
    """
    for r in renspecs:
        asset = r[0]
        from_defense = r[1]
        to_defense = r[2]

        for tag in scad['eom_etree'].findall('objects'):
            if tag.get('metaConcept') == asset:
                for evidence in tag.findall('evidenceAttributes'):
                    if evidence.get('metaConcept') == from_defense:
                        evidence.set('metaConcept', to_defense)

        for tag in scad['eom_etree'].findall('defenseDefaultValueConfigurations'):
            if tag.get('metaConcept') == asset:
                for defense in tag.findall('attributeConfigurations'):
                    if defense.get('metaConcept') == from_defense:
                        defense.set('metaConcept', to_defense)

    return


def add_attacksteps(scad, attacksteps):
    """
    Add attacksteps (a list of tuples (<asset name>, <attackstep name>)) to .eom (string).
    Returns the updated .eom as a string
    """
    for a in attacksteps:
        asset = a[0]
        attackstep = a[1]
        for dtag in scad['eom_etree'].findall('objects'):
            if dtag.get('metaConcept') == asset:
                aselem = ET.fromstring(f'<evidenceAttributes metaConcept="{attackstep}" />')
                dtag.append(aselem)

    return

def add_object(scad, o):
    ## ADDS A NEW OBJECT TO THE EOM ##

    obj = ET.SubElement(scad['eom_etree'], 'objects')
    obj.attrib['description'] = ""
    obj.attrib['id'] = o['id']
    obj.attrib['name'] = o['name']
    obj.attrib['metaConcept'] = o['metaConcept']
    obj.attrib['template'] = "false"
    obj.attrib['exportedId'] = o['exportedId']
    if (o['tag']):
        for k, v in o['tag'].items():
            if (k == "name" or k == "id"):
                continue
            else:
                s = f'"{k}":"{v[0]}"'
                #print(s)
                obj.attrib['attributesJsonString']= "{" + s + "}"
    

    existence = ET.SubElement(obj, "existence")
    existence.attrib['type']="FixedBoolean"
    param = ET.SubElement(existence, "parameters")
    param.attrib['name'] = "fixed"
    param.attrib['value'] = "1.0"

def add_association(scad, a):
    # assoc = {sourceObj: id of sourceProperty: role of targetObj, , }
    
    assoc = ET.SubElement(scad['eom_etree'], 'associations')
    assoc.attrib['description']=""
    assoc.attrib['sourceObject']= a['sourceId']
    assoc.attrib['targetObject']= a['targetId']
    assoc.attrib['id']= a['id']
    assoc.attrib['sourceProperty']= a['targetRole']
    assoc.attrib['targetProperty']=a['sourceRole']
    #print(a['targetRole'], a['sourceRole'])

def set_attack_steps(scad):
    for o in scad['eom_etree'].findall('objects'):
        for a in scad['eom_etree'].findall('attributeConfigurations'):
            if (a.get('metaConcept') == o.get('metaConcept')):
                o.append(a)

def delete_all_objects_and_assocs(scad):
    
    for o in scad['eom_etree'].findall('objects'):
        scad['eom_etree'].remove(o)
    for a in scad['eom_etree'].findall('associations'):
        scad['eom_etree'].remove(a)
    
    return scad
def set_unactivated_defense(scad, objId, name):
    for o in scad['eom_etree'].findall('objects'):
        if(o.get('id') == objId):
            #evidenceAttributes- evidenceDistribution- parameters
            d = ET.SubElement(o, "evidenceAttributes")
            d.attrib['metaConcept'] = name

            e = ET.SubElement(d, "evidenceDistribution")
            e.attrib['type'] = "FixedBoolean"

            p = ET.SubElement(e, "parameters")
            p.attrib['name'] = "fixed"

            o.append(d)
            

def set_activated_defense(scad, objId, name):
    for o in scad['eom_etree'].findall('objects'):
        
        if(o.get('id') == objId):
            #evidenceAttributes- evidenceDistribution- parameters
            d = ET.SubElement(o, "evidenceAttributes")
            d.attrib['metaConcept'] = name

            e = ET.SubElement(d, "evidenceDistribution")
            e.attrib['type'] = "FixedBoolean"

            p = ET.SubElement(e, "parameters")
            p.attrib['name'] = "fixed"
            p.attrib['value'] = "1.0"

            # defense = ET.SubElement(o, "attributeConfigurations")
            # defense.attrib['metaConcept'] = name
            # defValue = ET.SubElement(defense, "defaultValue")
            # defValue.attrib['type'] = "fixed"
            # parameters = ET.SubElement(defValue, "parameters")
            # parameters.attrib['name'] = "fixed"
            

def _defense_xml(name):
    return f"""<attributeConfigurations metaConcept="{name}">
      <defaultValue type="FixedBoolean">
        <parameters name="fixed"/>
      </defaultValue>
    </attributeConfigurations>"""


def add_defenses(scad, defenses):
    """
    Add defenses (a list of tuples (<asset name>, <defense name>)) to .eom (string).
    Returns the updated .eom as a string
    """
    asset_defs = {}
    for d in defenses:
        asset_defs.setdefault(d[0], []).append(d[1])

    # Add defenses by asset
    for asset in asset_defs:

        # Check if asset already has defenses. If not add the defenseDefaultValueConfigurations tag
        # for the asset.
        has_asset_defs = False
        for tag in scad['eom_etree'].findall('defenseDefaultValueConfigurations'):
            if tag.get('metaConcept') == asset:
                has_asset_defs = True
                break

        if not has_asset_defs:
            scad['eom_etree'].append(ET.fromstring(f'<defenseDefaultValueConfigurations metaConcept="{asset}"/>'))

        for defense in asset_defs[asset]:
            for tag in scad['eom_etree'].findall('objects'):
                if tag.get('metaConcept') == asset:
                    dtag = ET.fromstring(f'<evidenceAttributes metaConcept="{defense}" />')
                    tag.append(dtag)

            for tag in scad['eom_etree'].findall('defenseDefaultValueConfigurations'):
                if tag.get('metaConcept') == asset:
                    dtag = ET.fromstring(_defense_xml(defense))
                    tag.append(dtag)

    return


# Fixme: Make sure attacker-connected attacksteps are correctly handled
def delete_attacksteps(scad, attacksteps):
    for a in attacksteps:
        asset = a[0]
        attackstep = a[1]
        for tag in scad['eom_etree'].findall('objects'):
            if tag.get('metaConcept') == asset:
                for astag in tag.findall('evidenceAttributes'):
                    if astag.get('metaConcept') == attackstep:
                        tag.remove(astag)

    return


def delete_defenses(scad, defenses):
    for d in defenses:
        asset = d[0]
        defense = d[1]
        for tag in scad['eom_etree'].findall('objects'):
            if tag.get('metaConcept') == asset:
                for astag in tag.findall('evidenceAttributes'):
                    if astag.get('metaConcept') == defense:
                        tag.remove(astag)
        # Fixme: Remove the 'defenseDefaultValueConfigurations' tag if it it becomes empty
        for tag in scad['eom_etree'].findall('defenseDefaultValueConfigurations'):
            if tag.get('metaConcept') == asset:
                for dtag in tag.findall('attributeConfigurations'):
                    if dtag.get('metaConcept') == defense:
                        tag.remove(dtag)
                if not tag.findall('attributeConfigurations'):
                    # This was the last defense for asset - remove tag
                    scad['eom_etree'].remove(tag)

    return


def get_modelinfo(scad):
    """
    Returns a dictionary containing info about the model
    """
    ret = {}
    ret['archive_contents'] = scad['zip'].namelist()
    ret['lang_id'] = scad['meta']["langID"]
    ret['lang_version'] = scad['meta']["langVersion"]
    ret['lang_info'] = scad['meta']["info"]
    ret['samples'] = scad['eom_etree'].attrib.get('samples') if scad['eom_etree'].attrib.get('samples') else 'default'
    ret['threshold'] = scad['eom_etree'].attrib.get('warningThreshold')
    ret['n_objects'] = len(scad['eom_etree'].findall('objects'))
    ret['n_assocs'] = len(scad['eom_etree'].findall('associations'))
    ret['n_views'] = len(scad['cmx_etree'].findall('view'))
    hvas = []
    for o in scad['eom_etree'].findall('objects'):
        a = o.findall("evidenceAttributes[@consequence]")
        for attackstep in a:
            asset = {}
            asset['id'] = o.get('id')
            asset['name'] = o.get('name')
            asset['class'] = o.get('metaConcept')
            asset['attackstep'] = attackstep.get('metaConcept')
            asset['consequence'] = attackstep.get('consequence')
            hvas.append(asset)
    ret['hva'] = hvas

    return ret


def _print_info(scad, level):
    if level == '0':
        minfo = get_modelinfo(scad)
        print("Archive contents")
        print("----------------")
        for file in minfo['archive_contents']:
            print(file)
        print()
        print("Language info")
        print("-------------")
        print(f"Name:       {minfo['lang_id']}")
        print(f"Version:    {minfo['lang_version']}")
        print(f"Info:       {minfo['lang_info']}")
        print()
        print("Model params")
        print("------------")
        print(f"Samples:    {minfo['samples']}")
        print(f"Threshold:  {minfo['threshold']}")
        print()
        print("Model info")
        print("----------")
        print(f"# objects:  {minfo['n_objects']}")
        print(f"# assocs:   {minfo['n_assocs']}")
        print(f"# views:    {minfo['n_views']}")
        print(f"HVAs:")
        for hva in minfo['hva']:
            print(f"- {hva['consequence']} on {hva['name']}.{hva['attackstep']} - Asset class: {hva['class']}, id: {hva['id']}")
    elif level == '1':
        print("Not implemented yet")
    elif level == 'm':
        print(scad['zip'].read("meta.json").decode("utf-8"))
    elif level == 'c':
        print(scad['zip'].read(scad['basename'] + ".cmxCanvas").decode("utf-8"))
    elif level == 'e':
        print(scad['zip'].read(scad['basename'] + ".eom").decode("utf-8"))


def _validate_archive(zf):
    eom_present = False
    cvx_present = False
    meta_present = False
    basename = ""

    for zobjinf in zf.infolist():
        m = re.fullmatch("(.*)\.(\w+)", zobjinf.filename)
        if m:
            if m.group(2) == "eom":
                basename = m.group(1)
                eom_present = True
            elif m.group(2) == "cmxCanvas":
                cvx_present = True
            elif m.group(1) == "meta" and m.group(2) == "json":
                meta_present = True

    if not eom_present or not cvx_present or not meta_present:
        raise Exception("meta.json, .eom or .cvxCanvas missing in archive. Not a proper .sCAD?")

    return basename


def _info_usage():
    print("""info mode switches
    -h       - this message
    -f scad  - input .sCAD file
    -l level - where level is one of
        0 - print summary
        1 - print a lot of stuff
        e - dump .eom
        c - dump .cvxCanvas
        m - dump meta.json
""")


def _info_main(argv):
    try:
        opts, args = getopt.getopt(argv[2:], "f:l:h", ["scad=", "level=", "help"])
    except getopt.GetoptError as err:
        print(err)
        _usage()
        sys.exit(2)

    infile = ""
    infolevel = ""
    for o, a in opts:
        if o in ("-h", "--help"):
            _info_usage()
            sys.exit()
        elif o in ("-f", "--scad"):
            infile = a
        elif o in ("-l", "--level"):
            infolevel = a
            if infolevel not in ['0', '1', 'c', 'e', 'm']:
                _info_usage()
                sys.exit()
        else:
            assert False, "unhandled option"

    if not infile or not infolevel:
        _usage()
        sys.exit(2)

    try:
        scad = open(infile)
    except Exception as e:
        sys.stderr.write(f"Could not open .sCAD file: {str(e)}\n")
        sys.exit(1)

    _print_info(scad, infolevel)


def _modify_usage():
    print("""modify mode switches
    -h           - This message
    -f scad      - Input .sCAD filename
    -o outfile   - Output .sCAD filename
    -v langver   - Set language version in meta.json
    -n langname  - Set language name in meta.json
    -i info      - Set language info string
    -s samples   - Set # samples. Use literal 'default' to clear for securiCAD default.
    -t threshold - Set infinity threshold.
    -a addspec   - Add attackstep or defense to asset with addspec on the form [A|D]<asset>.<attackstep_or_defense>.
                   Example "AApplication.CodeExec" to add attackstep, "DApplication.Harden" to add defense.
    -r renspec   - Rename asset/attackstep/defense, where renspec is
                   - <src>/<dst> to rename asset src to dst
                   - A<asset>.<src>/<dst> to rename attackstep src to dst for target asset.
                   - D<asset>.<src>/<dst> to rename defense src to dst for target asset.
    -d delspec   - Delete attackstep/defense, where delspec is
                   - A<asset>.<attackstep> to delete attackstep for asset.
                   - D<asset>.<defense> to delete defense for asset.

    Multiple -a, -d and -r switches can be specified.
    If multiple -r, -a and -d switches are specified, the renames (-r) will be done first, 
    then add (-a) and lastly delete (-d).
    If multiple -r are specified with attacksteps/defense renames targeting an also renamed asset, the
    attacksteps/defense renames are applied last and should reference the new asset name.
""")


def _modify_main(argv):
    try:
        opts, args = getopt.getopt(argv[2:], "f:o:v:n:i:s:t:a:r:d:h",
                                   ["scad=", "out=", "langver=", "langname=", "info=", "samples=",
                                    "threshold=", "add=", "rename=", "delete=", "help"])
    except getopt.GetoptError as err:
        print(err)
        _usage()
        sys.exit(2)

    infile = ""
    langver = None
    langname = None
    langinfo = None
    samples = None
    threshold = None
    outfile = ""
    new_defenses = []
    new_attacksteps = []
    ren_assets = []
    ren_attacksteps = []
    ren_defenses = []
    del_defenses = []
    del_attacksteps = []

    for o, a in opts:
        if o in ("-h", "--help"):
            _modify_usage()
            sys.exit()
        elif o in ("-f", "--scad"):
            infile = a
        elif o in ("-o", "--out"):
            outfile = a
        elif o in ("-v", "--langver"):
            langver = a
        elif o in ("-n", "--langname"):
            langname = a
        elif o in ("-i", "--langinfo"):
            langinfo = a
        elif o in ("-s", "--samples"):
            samples = a
        elif o in ("-t", "--threshold"):
            threshold = a
        elif o in ("-a", "--add"):
            if re.fullmatch("[AD]\w+\.\w+", a):
                m = re.fullmatch("([AD])(\w+)\.(\w+)", a)
                if m.group(1) == 'A':
                    new_attacksteps.append((m.group(2), m.group(3)))
                else:
                    new_defenses.append((m.group(2), m.group(3)))
            else:
                print("Bad addspec spec: " + a)
                exit(2)
        elif o in ("-r", "--rename"):
            if re.fullmatch("\w+\/\w+", a):
                m = re.fullmatch("(\w+)\/(\w+)", a)
                ren_assets.append((m.group(1), m.group(2)))
            elif re.fullmatch("[AD]\w+\.\w+\/\w+", a):
                m = re.fullmatch("([AD])(\w+)\.(\w+)\/(\w+)", a)
                if m.group(1) == 'A':
                    ren_attacksteps.append((m.group(2), m.group(3), m.group(4)))
                else:
                    ren_defenses.append((m.group(2), m.group(3), m.group(4)))
            else:
                print("Bad renspec: " + a)
                exit(2)
        elif o in ("-d", "--delete"):
            if re.fullmatch("[AD]\w+\.\w+", a):
                m = re.fullmatch("([AD])(\w+)\.(\w+)", a)
                if m.group(1) == 'A':
                    del_attacksteps.append((m.group(2), m.group(3)))
                else:
                    del_defenses.append((m.group(2), m.group(3)))
            else:
                print("Bad delspec: " + a)
                exit(2)
        else:
            assert False, "unhandled option"

    if not infile or not outfile:
        _usage()
        sys.exit(2)

    try:
        scad = open(infile)
    except Exception as e:
        sys.stderr.write(f"Could not open .sCAD file: {str(e)}\n")
        sys.exit(1)

    set_meta(scad, langver, langname, langinfo)
    set_samples(scad, samples)
    set_threshold(scad, threshold)

    try:
        rename_assets(scad, ren_assets)
        rename_attacksteps(scad, ren_attacksteps)
        rename_defenses(scad, ren_defenses)
        add_attacksteps(scad, new_attacksteps)
        add_defenses(scad, new_defenses)
        delete_attacksteps(scad, del_attacksteps)
        delete_defenses(scad, del_defenses)
    except Exception as e:
        sys.stderr.write(f"Failed to alter .sCAD: {str(e)}\n")

    try:
        to_file(scad, outfile)
    except Exception as e:
        sys.stderr.write(f"Failed to write modified .sCAD: {str(e)}\n")


def _usage():
    sys.stderr.write("""Usage:
    scad info -h
    scad info -l level -f scad
    scad modify -h
    scad modify -f infile -o outfile [-v ver] [-n name] [-i info] [-a addspec ...] [-r renspec ...] [-d delspec ...]
    scad help (print this message - use '-h' with 'info' and 'modify' for details)
""")


def main():
    if sys.version_info[0] != 3 or sys.version_info[1] < 6:
        sys.stderr.write("This program is written for Python 3, version 3.6 or higher")
        sys.exit(1)

    if len(sys.argv) < 2:
        _usage()
        sys.exit()

    if sys.argv[1] == "info":
        _info_main(sys.argv)
    elif sys.argv[1] == "modify":
        _modify_main(sys.argv)
    elif sys.argv[1] == "help":
        _usage()
        sys.exit()
    else:
        _usage()
        sys.exit(2)


#
# Set namespaces. This must apparently be done this globally. Potential negative effects to module users.
ET.register_namespace('com.foreseeti.kernalCAD', 'http:///com/foreseeti/ObjectModel.ecore')
ET.register_namespace('xmi', 'http://www.omg.org/XMI')
ET.register_namespace('com.foreseeti.securiCAD', 'http:///com/foreseeti/ModelViews.ecore')

if __name__ == "__main__":
    main()