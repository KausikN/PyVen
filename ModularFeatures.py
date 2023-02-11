'''
Add and remove Modular features to repositories

Format of a modular feature:
 - Put a folder inside ModularFeaturesData/
 - Name: FeatureName (Eg. "StreamlitGUI")
 - Add a folder called "Version1" inside the folder and put all required files inside for that version
 - While adding a included file, its heirarchy is replicated from inside the version folder
     - Eg. a file, "Version1/A/B/C.py will be added as A/B/C.py into the destination (Version Part will be removed)"
     - Use this to keep different version of same file in same heirarchy which can be added based on choices
     - Eg. Choosing between adding cv2/A/B/C.py or PIL/A/B/C.py to the same location A/B/C.py based on user choice cv2 or PIL
 - Add a file called "includes.json" inside the folder
    - A JSON object with the following format:
        {
            "common": [
                Path to files or dirs included in feature by default
            ],
            "special": {
                # List of files included when selecting a choice among choices - will be rendered as selectbox in streamlit UI
                "choiceBased": [ 
                    {
                        "name": Choices Feature Name (Eg. "Image Processing Library"),
                        "choices": [
                            {
                                "name": Choice Name (Eg. "PIL" or "cv2"),
                                "paths": Paths of files or dirs to include if this choice is selected
                            },
                            ...
                        ]   
                    },
                    ...
                ],
                # List of files included when ticking a box for a feature - will be rendered as checkbox in streamlit UI
                "checkBased": [
                    {
                        "name": Feature Name (Eg. "Use GPU?"),
                        "paths": Paths of files or dirs to include if this feature is ticked / checked for use
                    }
                ]
            }
        }

'''

# Imports
import os
import json
import shutil

# Main Vars
PYVEN_CONFIG = json.load(open("pyven_config.json", "r"))

# Util Functions
def JoinPath(*ops):
    return os.path.join(*ops).replace("\\", "/")

def GetVersionSplitPath(path):
    path = path.replace("\\", "/")
    versionSplit = path.split("/")
    versionDir = versionSplit[0]
    fileHeirarchy = '/'.join(versionSplit[1:])
    return [versionDir, fileHeirarchy]

def CheckDataSame(src, dst):
    if (not os.path.exists(src)) or (not os.path.exists(dst)):
        return False
    
    if os.path.isfile(src) and os.path.isfile(dst):
        return (open(src, 'r').read() == open(dst, 'r').read())
    elif os.path.isdir(src) and os.path.isdir(dst):
        for root, dirs, files in os.walk(src):
            for file in files:
                src_file = JoinPath(root, file)
                dst_file = JoinPath(dst, src_file.replace(src, "", 1))
                if (not os.path.exists(dst_file)):
                    return False
                if os.path.isfile(src_file) and os.path.isfile(dst_file):
                    if (open(src_file, 'r').read() != open(dst_file, 'r').read()):
                        return False
        return True
    return False

def CascadeCopyPath(path, save_parent, save_path, overwrite=True):
    if not overwrite:
        if os.path.exists(JoinPath(save_parent, save_path)):
            return

    path = path.replace("\\", "/")
    save_path = save_path.replace("\\", "/")

    saveSplit = save_path.split("/")
    saveDirPath = '/'.join(saveSplit[:-1]).rstrip("/")
    saveFile = saveSplit[-1]
    os.makedirs(JoinPath(save_parent, saveDirPath), exist_ok=True)
    if os.path.isfile(path):
        shutil.copy(path, JoinPath(save_parent, save_path))
    elif os.path.isdir(path):
        shutil.copytree(path, JoinPath(save_parent, save_path), dirs_exist_ok=True)

def CascadeRemovePath(path, remove_parent, remove_path, checkEdited=False):
    if checkEdited: # If edited dont delete
        if not CheckDataSame(path, JoinPath(remove_parent, remove_path)):
            return
    remove_path = remove_path.replace("\\", "/")
    remove_parent = remove_parent.replace("\\", "/")
    full_remove_path = JoinPath(remove_parent, remove_path)
    remove_dirs = os.path.split(remove_path)[0]

    if os.path.exists(full_remove_path):
        if os.path.isfile(full_remove_path):
            os.remove(full_remove_path)
        elif os.path.isdir(full_remove_path):
            shutil.rmtree(full_remove_path)
        if not (remove_dirs.strip() == ""):
            try:
                os.removedirs(JoinPath(remove_parent, remove_dirs))
            except:
                pass

# Main Functions
def ModularFeature_Check(repo_path):
    if PYVEN_CONFIG["pyven_dir"] not in os.listdir(repo_path):
        return None
    else:
        ADDED_FEATURES = json.load(open(JoinPath(repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"]), 'r'))["added_features"]
        return ADDED_FEATURES

def ModularFeature_Load(feature_path):
    FEATURE_INCLUDES = json.load(open(os.path.join(feature_path, 'includes.json')))
    FEATURE_VERSIONS = []
    for p in os.listdir(feature_path):
        if os.path.isdir(p):
            FEATURE_VERSIONS.append(p)
    FEATURE = {
        "path": feature_path,
        "includes": FEATURE_INCLUDES,
        "versions": FEATURE_VERSIONS
    }
    return FEATURE

def ModularFeature_Add(feature_path, add_repo_path, special_includes_inputs, DisplayWidget=None, SafeMode=False):
    FEATURE = ModularFeature_Load(feature_path)
    # Add Common Files
    i=0
    for f in FEATURE["includes"]["common"]:
        i+=1
        if DisplayWidget is not None: DisplayWidget.markdown("Adding Common Files: " + "[" + str(i) + " / " + str(len(FEATURE["includes"]["common"])) + "]")
        load_f = JoinPath(feature_path, f)
        save_f = GetVersionSplitPath(f)[1]
        CascadeCopyPath(load_f, add_repo_path, save_f, overwrite=not SafeMode)
    # Add Special Files
    to_add_paths = []
    # Choice Based
    for choiceDataKey in FEATURE["includes"]["special"]["choiceBased"].keys():
        choiceData = FEATURE["includes"]["special"]["choiceBased"][choiceDataKey]
        choiceIndex = special_includes_inputs["choiceBased"][choiceDataKey]
        fs = choiceData["choices"][choiceIndex]["paths"]
        for f in fs:
            load_f = JoinPath(feature_path, f)
            save_f = GetVersionSplitPath(f)[1]
            to_add_paths.append([load_f, save_f])
    # Check Based
    for checkDataKey in FEATURE["includes"]["special"]["checkBased"].keys():
        checkData = FEATURE["includes"]["special"]["checkBased"][checkDataKey]
        if special_includes_inputs["checkBased"][checkDataKey]:
            fs = checkData["paths"]
            for f in fs:
                load_f = JoinPath(feature_path, f)
                save_f = GetVersionSplitPath(f)[1]
                to_add_paths.append([load_f, save_f])
    
    i=0
    for load_f, save_f in to_add_paths:
        i+=1
        if DisplayWidget is not None: DisplayWidget.markdown("Adding Special Files: " + "[" + str(i) + " / " + str(len(to_add_paths)) + "]")
        CascadeCopyPath(load_f, add_repo_path, save_f, overwrite=not SafeMode)

def ModularFeature_Remove(feature_path, remove_repo_path, DisplayWidget=None, SafeMode=False):
    feature_name = feature_path.split("/")[-1]
    remove_repo_name = remove_repo_path.split("/")[-1]
    FEATURE = ModularFeature_Load(feature_path)

    # Get Special Inputs used
    features_pyven_repo_path = JoinPath(remove_repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"])
    added_features_data = json.load(open(features_pyven_repo_path, 'r'))["added_features"]
    if feature_name not in added_features_data.keys():
        if DisplayWidget is not None: DisplayWidget.markdown("Feature " + feature_name + " not added to " + remove_repo_name + ".")
        return
    special_includes_inputs = added_features_data[feature_name]["special"]

    # Remove Common Files
    i=0
    for f in FEATURE["includes"]["common"]:
        i+=1
        if DisplayWidget is not None: DisplayWidget.markdown("Removing Common Files: " + "[" + str(i) + " / " + str(len(FEATURE["includes"]["common"])) + "]")
        load_f = JoinPath(feature_path, f)
        saved_f = GetVersionSplitPath(f)[1]
        CascadeRemovePath(load_f, remove_repo_path, saved_f, checkEdited=SafeMode)

    # Remove Special Files
    to_remove_paths = []
    # Choice Based
    for choiceDataKey in FEATURE["includes"]["special"]["choiceBased"].keys():
        choiceData = FEATURE["includes"]["special"]["choiceBased"][choiceDataKey]
        choiceIndex = special_includes_inputs["choiceBased"][choiceDataKey]
        fs = choiceData["choices"][choiceIndex]["paths"]
        for f in fs:
            load_f = JoinPath(feature_path, f)
            save_f = GetVersionSplitPath(f)[1]
            to_remove_paths.append([load_f, save_f])
    # Check Based
    for checkDataKey in FEATURE["includes"]["special"]["checkBased"].keys():
        checkData = FEATURE["includes"]["special"]["checkBased"][checkDataKey]
        if checkDataKey in special_includes_inputs["checkBased"].keys() \
            and special_includes_inputs["checkBased"][checkDataKey]:
            fs = checkData["paths"]
            for f in fs:
                load_f = JoinPath(feature_path, f)
                save_f = GetVersionSplitPath(f)[1]
                to_remove_paths.append([load_f, save_f])
    
    i=0
    for load_f, save_f in to_remove_paths:
        i+=1
        if DisplayWidget is not None: DisplayWidget.markdown("Removing Special Files: " + "[" + str(i) + " / " + str(len(to_remove_paths)) + "]")
        CascadeRemovePath(load_f, remove_repo_path, save_f, checkEdited=SafeMode)


# Driver Code