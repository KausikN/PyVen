"""
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
                "choice_based": [ 
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
                "check_based": [
                    {
                        "name": Feature Name (Eg. "Use GPU?"),
                        "paths": Paths of files or dirs to include if this feature is ticked / checked for use
                    }
                ]
            }
        }

"""

# Imports
import os
import json
import shutil

# Main Vars
PYVEN_CONFIG = json.load(open("pyven_config.json", "r"))

# Main Functions
# Util Functions
def JoinPath(*ops):
    '''
    Utils - Join paths
    '''
    return os.path.join(*ops).replace("\\", "/")

def GetVersionSplitPath(path):
    '''
    Utils - Split path into version and file heirarchy
    '''
    path = path.replace("\\", "/")
    versionSplit = path.split("/")
    versionDir = versionSplit[0]
    fileHeirarchy = '/'.join(versionSplit[1:])
    return versionDir, fileHeirarchy

def CheckDataSame(src, dst):
    '''
    Utils - Check if data in src and dst are same
    '''
    # Check if both exist
    if (not os.path.exists(src)) or (not os.path.exists(dst)): return False
    # Check if both are files, if yes compare
    if os.path.isfile(src) and os.path.isfile(dst): return (open(src, "r").read() == open(dst, "r").read())
    # Check if both are dirs, if yes compare all files within them
    elif os.path.isdir(src) and os.path.isdir(dst):
        for root, dirs, files in os.walk(src):
            for file in files:
                src_file = JoinPath(root, file)
                dst_file = JoinPath(dst, src_file.replace(src, "", 1))
                if (not os.path.exists(dst_file)): return False
                if os.path.isfile(src_file) and os.path.isfile(dst_file):
                    if (open(src_file, 'r').read() != open(dst_file, 'r').read()): return False
        return True
    return False

def CascadeCopyPath(path, save_parent, save_path, overwrite=True):
    '''
    Utils - Copy path to save_path (Cascade copy)
    '''
    # Check if already exists
    if not overwrite:
        if os.path.exists(JoinPath(save_parent, save_path)): return
    # Init
    path = path.replace("\\", "/")
    save_path = save_path.replace("\\", "/")
    save_split = save_path.split("/")
    save_dir_path = '/'.join(save_split[:-1]).rstrip("/")
    save_file = save_split[-1]
    # Copy
    os.makedirs(JoinPath(save_parent, save_dir_path), exist_ok=True)
    if os.path.isfile(path): shutil.copy(path, JoinPath(save_parent, save_path))
    elif os.path.isdir(path): shutil.copytree(path, JoinPath(save_parent, save_path), dirs_exist_ok=True)

def CascadeRemovePath(path, remove_parent, remove_path, check_edited=False):
    '''
    Utils - Remove path from remove_path (Cascade remove)
    '''
    # Check if already removed
    if check_edited: # If edited dont delete
        if not CheckDataSame(path, JoinPath(remove_parent, remove_path)): return
    # Init
    remove_path = remove_path.replace("\\", "/")
    remove_parent = remove_parent.replace("\\", "/")
    full_remove_path = JoinPath(remove_parent, remove_path)
    remove_dirs = os.path.split(remove_path)[0]
    # Remove
    if os.path.exists(full_remove_path):
        if os.path.isfile(full_remove_path): os.remove(full_remove_path)
        elif os.path.isdir(full_remove_path): shutil.rmtree(full_remove_path)
        if not (remove_dirs.strip() == ""):
            try: os.removedirs(JoinPath(remove_parent, remove_dirs))
            except: pass

# Modular Feature Functions
def ModularFeature_Check(repo_path):
    '''
    Modular Feature - Check if repo has modular features
    '''
    # Check if pyven dir exists
    if PYVEN_CONFIG["pyven_dir"] not in os.listdir(repo_path): return None
    # Return added features
    return json.load(open(JoinPath(repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"]), "r"))["added_features"]

def ModularFeature_Load(feature_path):
    '''
    Modular Feature - Load modular feature
    '''
    # Load Feature
    FEATURE_INCLUDES = json.load(open(os.path.join(feature_path, "includes.json")))
    # Get Versions
    FEATURE_VERSIONS = []
    for p in os.listdir(feature_path):
        if os.path.isdir(p): FEATURE_VERSIONS.append(p)
    # Form Feature
    FEATURE = {
        "path": feature_path,
        "includes": FEATURE_INCLUDES,
        "versions": FEATURE_VERSIONS
    }

    return FEATURE

def ModularFeature_Add(feature_path, add_repo_path, special_includes_inputs, DISPLAY_WIDGET=None, SAFE_MODE=False):
    '''
    Modular Feature - Add modular feature
    '''
    # Load Feature
    FEATURE = ModularFeature_Load(feature_path)
    # Add Common Files
    i = 0
    for f in FEATURE["includes"]["common"]:
        i += 1
        if DISPLAY_WIDGET is not None: DISPLAY_WIDGET.markdown("Adding Common Files: " + "[" + str(i) + " / " + str(len(FEATURE["includes"]["common"])) + "]")
        load_f = JoinPath(feature_path, f)
        save_f = GetVersionSplitPath(f)[1]
        CascadeCopyPath(load_f, add_repo_path, save_f, overwrite=not SAFE_MODE)
    # Add Special Files
    to_add_paths = []
    ## Choice Based
    for choice_data_key in FEATURE["includes"]["special"]["choice_based"].keys():
        choice_data = FEATURE["includes"]["special"]["choice_based"][choice_data_key]
        choice_index = special_includes_inputs["choice_based"][choice_data_key]
        fs = choice_data["choices"][choice_index]["paths"]
        for f in fs:
            load_f = JoinPath(feature_path, f)
            save_f = GetVersionSplitPath(f)[1]
            to_add_paths.append([load_f, save_f])
    ## Check Based
    for check_data_key in FEATURE["includes"]["special"]["check_based"].keys():
        check_data = FEATURE["includes"]["special"]["check_based"][check_data_key]
        if special_includes_inputs["check_based"][check_data_key]:
            fs = check_data["paths"]
            for f in fs:
                load_f = JoinPath(feature_path, f)
                save_f = GetVersionSplitPath(f)[1]
                to_add_paths.append([load_f, save_f])
    # Add
    i = 0
    for load_f, save_f in to_add_paths:
        i += 1
        if DISPLAY_WIDGET is not None: DISPLAY_WIDGET.markdown("Adding Special Files: " + "[" + str(i) + " / " + str(len(to_add_paths)) + "]")
        CascadeCopyPath(load_f, add_repo_path, save_f, overwrite=not SAFE_MODE)

def ModularFeature_Remove(feature_path, remove_repo_path, DISPLAY_WIDGET=None, SAFE_MODE=False):
    '''
    Modular Feature - Remove modular feature
    '''
    # Load Feature
    feature_name = feature_path.split("/")[-1]
    remove_repo_name = remove_repo_path.split("/")[-1]
    FEATURE = ModularFeature_Load(feature_path)

    # Get Special Inputs used
    features_pyven_repo_path = JoinPath(remove_repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"])
    added_features_data = json.load(open(features_pyven_repo_path, 'r'))["added_features"]
    if feature_name not in added_features_data.keys():
        if DISPLAY_WIDGET is not None: DISPLAY_WIDGET.markdown("Feature " + feature_name + " not added to " + remove_repo_name + ".")
        return
    special_includes_inputs = added_features_data[feature_name]["special"]

    # Remove Common Files
    i=0
    for f in FEATURE["includes"]["common"]:
        i+=1
        if DISPLAY_WIDGET is not None: DISPLAY_WIDGET.markdown("Removing Common Files: " + "[" + str(i) + " / " + str(len(FEATURE["includes"]["common"])) + "]")
        load_f = JoinPath(feature_path, f)
        saved_f = GetVersionSplitPath(f)[1]
        CascadeRemovePath(load_f, remove_repo_path, saved_f, check_edited=SAFE_MODE)

    # Remove Special Files
    to_remove_paths = []
    # Choice Based
    for choice_data_key in FEATURE["includes"]["special"]["choice_based"].keys():
        choice_data = FEATURE["includes"]["special"]["choice_based"][choice_data_key]
        choice_index = special_includes_inputs["choice_based"][choice_data_key]
        fs = choice_data["choices"][choice_index]["paths"]
        for f in fs:
            load_f = JoinPath(feature_path, f)
            save_f = GetVersionSplitPath(f)[1]
            to_remove_paths.append([load_f, save_f])
    # Check Based
    for check_data_key in FEATURE["includes"]["special"]["check_based"].keys():
        check_data = FEATURE["includes"]["special"]["check_based"][check_data_key]
        if check_data_key in special_includes_inputs["check_based"].keys() \
            and special_includes_inputs["check_based"][check_data_key]:
            fs = check_data["paths"]
            for f in fs:
                load_f = JoinPath(feature_path, f)
                save_f = GetVersionSplitPath(f)[1]
                to_remove_paths.append([load_f, save_f])
    # Remove
    i = 0
    for load_f, save_f in to_remove_paths:
        i += 1
        if DISPLAY_WIDGET is not None: DISPLAY_WIDGET.markdown("Removing Special Files: " + "[" + str(i) + " / " + str(len(to_remove_paths)) + "]")
        CascadeRemovePath(load_f, remove_repo_path, save_f, check_edited=SAFE_MODE)