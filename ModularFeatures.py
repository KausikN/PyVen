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

# Util Functions
def JoinPath(*ops):
    return os.path.join(*ops).replace("\\", "/")

def GetVersionSplitPath(path):
    path = path.replace("\\", "/")
    versionSplit = path.split("/")
    versionDir = versionSplit[0]
    fileHeirarchy = '/'.join(versionSplit[1:])
    return [versionDir, fileHeirarchy]

def CascadeCreatePath(path, save_parent, save_path, overwrite=True):
    if not overwrite:
        if os.path.exists(JoinPath(save_parent, save_path)):
            return

    path = path.replace("\\", "/")
    save_path = save_path.replace("\\", "/")

    saveSplit = save_path.split("/")
    saveDirPath = '/'.join(saveSplit[:-1]).rstrip("/")
    saveFile = saveSplit[-1]
    if os.path.isdir(path):
        saveDirPath = JoinPath(saveDirPath, saveFile)
    os.makedirs(JoinPath(save_parent, saveDirPath), exist_ok=True)
    if os.path.isfile(path):
        shutil.copy(path, JoinPath(save_parent, save_path))

# Main Functions
def ModularFeature_Check(repo_path):
    if ".pyven" not in os.listdir(repo_path):
        return None
    else:
        ADDED_FEATURES = json.load(open(JoinPath(repo_path, ".pyven/features.json"), 'r'))["added_features"]
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

def ModularFeature_Add(feature_path, add_repo_path, special_includes_inputs, DisplayWidget=None):
    FEATURE = ModularFeature_Load(feature_path)
    # Add Common Files
    i=0
    for f in FEATURE["includes"]["common"]:
        i+=1
        if DisplayWidget is not None: DisplayWidget.markdown("Adding Common Files: " + "[" + str(i) + " / " + str(len(FEATURE["includes"]["common"])) + "]")
        load_f = JoinPath(feature_path, f)
        save_f = GetVersionSplitPath(f)[1]
        CascadeCreatePath(load_f, add_repo_path, save_f)
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
        CascadeCreatePath(load_f, add_repo_path, save_f)


# Driver Code