"""
Stream lit GUI for hosting PyVen
"""

# Imports
import os
import json
import streamlit as st

import PyVen
from ModularFeatures import *

# Main Vars
config = json.load(open("./StreamLitGUI/UIConfig.json", "r"))

# Main Functions
def main():
    # Create Sidebar
    selected_box = st.sidebar.selectbox(
    "Choose one of the following",
        tuple(
            [config["PROJECT_NAME"]] + 
            config["PROJECT_MODES"]
        )
    )
    
    if selected_box == config["PROJECT_NAME"]:
        HomePage()
    else:
        correspondingFuncName = selected_box.replace(" ", "_").lower()
        if correspondingFuncName in globals().keys():
            globals()[correspondingFuncName]()
 

def HomePage():
    st.title(config["PROJECT_NAME"])
    st.markdown("Github Repo: " + "[" + config["PROJECT_LINK"] + "](" + config["PROJECT_LINK"] + ")")
    st.markdown(config["PROJECT_DESC"])
    # st.write(open(config["PROJECT_README"], "r").read())

#############################################################################################################################
# Repo Based Vars
PATHS = {
    "cache": "StreamLitGUI/CacheData/Cache.json",
    "features": "ModularFeaturesData/",
}
DEFAULT_FEATURE_NAME_PYVENSTARTER = "PyVenStarter"

# Util Vars
CACHE = {}
FEATURES = {}

# Util Functions
def LoadCache():
    '''
    Load Cache
    '''
    global CACHE
    CACHE = json.load(open(PATHS["cache"], "r"))

def SaveCache():
    '''
    Save Cache
    '''
    global CACHE
    json.dump(CACHE, open(PATHS["cache"], "w"), indent=4)

# Load Functions
def LoadFeatures():
    '''
    Load Features
    '''
    global FEATURES
    for f in os.listdir(PATHS["features"]): FEATURES[f] = JoinPath(PATHS["features"], f)

def LoadPyVenFeaturesMetadata(repo_path):
    '''
    Load PyVen Features Metadata
    '''
    return json.load(open(JoinPath(repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"]), "r"))

def SavePyVenFeaturesMetadata(repo_path, FEATURES_DATA):
    '''
    Save PyVen Features Metadata
    '''
    json.dump(FEATURES_DATA, open(JoinPath(repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"]), "w"), indent=4)

def SavePyVenModulesMetadata(repo_path, MODULES_DATA):
    '''
    Save PyVen Modules Metadata
    '''
    json.dump(MODULES_DATA, open(JoinPath(repo_path, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["modules"]), "w"), indent=4)

# Main Functions
def RebuildModules(REPO_PATH, PROGRESS_OBJ=None):
    '''
    Rebuild Modules
    '''
    MODULES = PyVen.Repo_FindModules(REPO_PATH, PROGRESS_OBJ=PROGRESS_OBJ)
    SavePyVenModulesMetadata(REPO_PATH, MODULES)
    return MODULES

def UpdateRepoBasicDetails(REPO_PATH, REPO_NAME):
    '''
    Update Repo Basic Details
    '''
    BasicInfo = json.load(open(JoinPath(REPO_PATH, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["basic_info"]), "r"))
    BasicInfo["repo_name"] = REPO_NAME
    requirements = []
    if "requirements.txt" in os.listdir(REPO_PATH):
        requirements = [
            line.strip() 
            for line in open(JoinPath(REPO_PATH, "requirements.txt"), "r").readlines() 
            if (line.strip() not in [""]) and (not line.strip().startswith("#"))
        ]
    BasicInfo["requirements"] = requirements
    json.dump(BasicInfo, open(JoinPath(REPO_PATH, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["basic_info"]), "w"), indent=4)

# UI Functions
def UI_LoadRepos(parent_paths):
    '''
    UI - Load Repos
    '''
    # Init
    path_count = len(parent_paths)
    # Load Repos
    LoaderText = st.empty()
    REPO_PATHS = []
    i = 0
    for parent_path in parent_paths:
        ## Load Local Repos
        repo_paths = PyVen.Repo_GetLocalRepos(parent_path)
        REPO_PATHS.extend(repo_paths)
        ## Update
        i += 1
        LoaderText.markdown("[" + str(i) + " / " + str(path_count) + "] Loaded " + parent_path)
    # Remove Duplicates
    REPO_PATHS = list(set(REPO_PATHS))
    LoaderText.markdown("Loaded " + str(len(REPO_PATHS)) + " repos.")
    # Form Repo Data
    REPO_DATAS = [{
        "name": os.path.split(repo_path.rstrip("/"))[-1],
        "path": repo_path
    } for repo_path in REPO_PATHS]
    ## Sort Repo Data based on name
    REPO_DATAS = sorted(REPO_DATAS, key=lambda x: x["name"])

    return REPO_DATAS

def UI_DisplayRepoTreeData(repo):
    '''
    UI - Display Repo Tree Data
    '''
    # Display Repo Details
    st.markdown("## " + repo["name"])
    st.markdown("<a href=" + repo["repo_link"] + ">" + repo["repo_link"] + "</a>", unsafe_allow_html=True)
    st.markdown(repo["local_path"])
    # Display Modules
    modules_keys = list(repo["modules"].keys())
    modules_names = [repo["modules"][k]["name"] for k in modules_keys]
    st.markdown("## Modules")
    USERINPUT_ModuleName = st.selectbox("Select Module", ["Select Module"] + modules_names)
    if USERINPUT_ModuleName == "Select Module": return
    USEINPUT_Module = repo["modules"][modules_keys[modules_names.index(USERINPUT_ModuleName)]]
    st.markdown("### " + USEINPUT_Module["name"])
    detail_size_ratio = [1, 3]
    col1, col2 = st.columns(detail_size_ratio)
    col1.markdown("Module Type:")
    col2.markdown(USEINPUT_Module["type"])
    col1, col2 = st.columns(detail_size_ratio)
    col1.markdown("Module Heirarchy:")
    col2.markdown(".".join(USEINPUT_Module["sub_dir"].split("/") + [USEINPUT_Module["name"]]), unsafe_allow_html=True)
    if USEINPUT_Module["type"] == "local":
        col1, col2 = st.columns(detail_size_ratio)
        col1.markdown("File Link:")
        col2.markdown("<a href=" + USEINPUT_Module["link"] + ">" + USEINPUT_Module["link"] + "</a>", unsafe_allow_html=True)
        col1, col2 = st.columns(detail_size_ratio)
        col1.markdown("Dependencies:")
        deps = [repo["modules"][key]["name"] for key in USEINPUT_Module["dependencies"]]
        col2.markdown(", ".join(deps))

def UI_GetFeatureParams(feature_path, defaults=None, NCOLS=3):
    '''
    UI - Get Feature Params
    '''
    # Load Feature Includes
    includes = json.load(open(JoinPath(feature_path, "includes.json"), "r"))
    special_inputs = {"choice_based": {}, "check_based": {}}
    # Choice Based
    choice_based_data = includes["special"]["choice_based"]
    n_choice_params = len(choice_based_data.keys())
    choice_based_data_labels = list(choice_based_data.keys())
    params_done = 0
    while(params_done < n_choice_params):
        params_todo = min(NCOLS, n_choice_params-params_done)
        cols = st.columns(params_todo)
        for i in range(params_todo):
            choice_data_key = choice_based_data_labels[params_done + i]
            # choice_names = [choice_based_data[choice_data_key]["choices"][k] for k in choice_based_data[choice_data_key]["choices"].keys()]
            choice_names = [k["name"] for k in choice_based_data[choice_data_key]["choices"]]
            default_val = 0 if defaults is None else defaults["choice_based"][choice_data_key]
            inp = cols[i].selectbox(choice_based_data[choice_data_key]["label"], choice_names, index=default_val)
            inp_index = choice_names.index(inp)
            special_inputs["choice_based"][choice_data_key] = inp_index
        params_done += params_todo
    # Check Based
    check_based_data = includes["special"]["check_based"]
    n_check_params = len(check_based_data.keys())
    check_based_data_labels = list(check_based_data.keys())
    params_done = 0
    while(params_done < n_check_params):
        params_todo = min(NCOLS, n_check_params-params_done)
        cols = st.columns(params_todo)
        for i in range(params_todo):
            check_data_key = check_based_data_labels[params_done + i]
            default_val = False if defaults is None else defaults["check_based"][check_data_key]
            inp = st.checkbox(check_based_data[check_data_key]["label"], default_val)
            special_inputs["check_based"][check_data_key] = inp
        params_done += params_todo
    
    return special_inputs

def UI_CheckPyVenInit(REPO_PATH, REPO_NAME):
    '''
    UI - Check PyVen Init
    '''
    # Check if PyVen Initialised in repo
    if PYVEN_CONFIG["pyven_dir"] not in os.listdir(REPO_PATH):
        InitButton = st.empty()
        if InitButton.button("Initialise PyVen for the Repo"):
            ## Add PyVen Starter Feature
            USERINPUT_FeatureChoice = FEATURES[DEFAULT_FEATURE_NAME_PYVENSTARTER]
            LoaderWidget = st.empty()
            ModularFeature_Add(USERINPUT_FeatureChoice, REPO_PATH, {"choice_based": {}, "check_based": {}}, LoaderWidget)
            ## Update Modules in pyven_dir
            RebuildModules(REPO_PATH, PROGRESS_OBJ=st.progress(0.0))
            ## Update basic_info.json
            UpdateRepoBasicDetails(REPO_PATH, REPO_NAME)
            ## Display
            LoaderWidget.markdown("Repo initialised with PyVen!")
            InitButton.markdown("")
            return True
        else:
            return False
    return True

def UI_SearchModePrune(REPO_DATAS, REPO_NAMES):
    '''
    UI - Search Mode Prune
    '''
    global FEATURES
    # Search Mode
    USERINPUT_SearchMode = st.selectbox("Search Mode", ["Search by Repo Name", "Search by Added Features"])
    if USERINPUT_SearchMode == "Search by Repo Name":
        return REPO_DATAS, REPO_NAMES
    elif USERINPUT_SearchMode == "Search by Added Features":
        USERINPUT_RequiredFeatures = st.multiselect("Features", list(FEATURES.keys()))
        if len(USERINPUT_RequiredFeatures) == 0: return REPO_DATAS, REPO_NAMES
        REPO_DATAS_PRUNED, REPO_NAMES_PRUNED = [], []
        for repo in REPO_DATAS:
            repo_path = repo["path"]
            if PYVEN_CONFIG["pyven_dir"] not in os.listdir(repo_path): # Repo not initialised with pyven
                continue
            features_data = LoadPyVenFeaturesMetadata(repo_path)
            features_names = list(features_data["added_features"].keys())
            if(set(USERINPUT_RequiredFeatures).issubset(set(features_names))):
                REPO_DATAS_PRUNED.append(repo)
                REPO_NAMES_PRUNED.append(repo["name"])
        return REPO_DATAS_PRUNED, REPO_NAMES_PRUNED

# Repo Based Functions
def analyse_repo():
    global FEATURES
    global CACHE

    # Title
    st.header("Analyse Local Repo")

    LoadCache()
    LoadFeatures()
    REPO_NAMES = [repo["name"] for repo in CACHE["GIT_REPOS"]]
    REPO_DATAS = CACHE["GIT_REPOS"]

    # Load Inputs
    USERINPUT_RebuildPyVenData = st.sidebar.button("Rebuild PyVen Data")

    REPO_DATAS_PRUNED, REPO_NAMES_PRUNED = UI_SearchModePrune(REPO_DATAS, REPO_NAMES)

    USERINPUT_RepoChoiceName = st.selectbox("Select Repo", ["Select Repo"] + REPO_NAMES_PRUNED)
    if USERINPUT_RepoChoiceName == "Select Repo": return
    USERINPUT_RepoChoice = REPO_DATAS_PRUNED[REPO_NAMES_PRUNED.index(USERINPUT_RepoChoiceName)]

    # Process Inputs
    # Load Repo
    REPO_PATH = USERINPUT_RepoChoice["path"]
    REPO_NAME = USERINPUT_RepoChoice["name"]

    if USERINPUT_RebuildPyVenData:
        REPO_TREE = RebuildModules(REPO_PATH, PROGRESS_OBJ=st.sidebar.progress(0.0))
        UpdateRepoBasicDetails(REPO_PATH, REPO_NAME)
        st.sidebar.markdown("Rebuilt PyVen Data for " + REPO_NAME + "!")
    elif not (REPO_NAME == CACHE["analyse_repo_current"]["name"]):
        REPO_TREE = PyVen.Repo_FindModules(REPO_PATH, PROGRESS_OBJ=st.progress(0.0))
    else:
        REPO_TREE = CACHE["analyse_repo_current"]["repo_tree"]

    # Display Outputs
    UI_DisplayRepoTreeData(REPO_TREE)

    # Check if PyVen Features Added
    st.markdown("## Features Added")
    ADDED_FEATURES = ModularFeature_Check(REPO_PATH)
    if ADDED_FEATURES is None:
        st.warning("Repo not initialsed with PyVen.")
    else:
        USERINPUT_AddedFeaturesChoice = st.selectbox("Added Features", ADDED_FEATURES)

    # Save Cache
    if not (REPO_NAME == CACHE["analyse_repo_current"]):
        CACHE["analyse_repo_current"]["name"] = REPO_NAME
        CACHE["analyse_repo_current"]["repo_tree"] = REPO_TREE
        SaveCache()

def edit_repo_features():
    global FEATURES

    # Title
    st.header("Edit Repo Features")

    LoadCache()
    LoadFeatures()
    REPO_NAMES = [repo["name"] for repo in CACHE["GIT_REPOS"]]
    REPO_DATAS = CACHE["GIT_REPOS"]

    # Load Inputs
    USERINPUT_SafeUpdate = st.sidebar.checkbox("Safe Update/Remove", True)
    USERINPUT_RebuildPyVenData = st.sidebar.button("Rebuild PyVen Data")

    USERINPUT_RepoChoiceName = st.selectbox("Select Repo", ["Select Repo"] + REPO_NAMES)
    if USERINPUT_RepoChoiceName == "Select Repo": return
    USERINPUT_RepoChoice = REPO_DATAS[REPO_NAMES.index(USERINPUT_RepoChoiceName)]
    REPO_PATH = USERINPUT_RepoChoice["path"]
    REPO_NAME = USERINPUT_RepoChoice["name"]

    # Check if PyVen Initialised in repo
    if not UI_CheckPyVenInit(REPO_PATH, REPO_NAME): return

    USERINPUT_FeatureChoiceName = st.selectbox("Select Feature", ["Select Feature"] + list(FEATURES.keys()), index=1)
    if USERINPUT_FeatureChoiceName == "Select Feature": return
    USERINPUT_FeatureChoice = FEATURES[USERINPUT_FeatureChoiceName]

    features_pyven_repo_path = JoinPath(REPO_PATH, PYVEN_CONFIG["pyven_dir"], PYVEN_CONFIG["pyven_files"]["features"])
    added_features_data = json.load(open(features_pyven_repo_path, "r"))["added_features"]
    button_name = "Add"
    feature_exists = False
    special_inputs_default = None
    if USERINPUT_FeatureChoiceName not in added_features_data.keys():
        st.markdown("Feature " + USERINPUT_FeatureChoiceName + " not yet added to " + REPO_NAME + ".")
    else:
        st.markdown("Feature " + USERINPUT_FeatureChoiceName + " already added in " + REPO_NAME + ".")
        button_name = "Update"
        feature_exists = True
        # special_inputs_default = added_features_data[USERINPUT_FeatureChoiceName]["special"] # Commented as this messes up the UI

    special_inputs = UI_GetFeatureParams(USERINPUT_FeatureChoice, special_inputs_default)

    # Process Inputs
    col1, col2 = st.columns(2)
    bcol1 = col1.empty()
    bcol2 = col2.empty()
    if bcol1.button(button_name + " Feature", key="BA1"):
        LoaderWidget = st.empty()
        if feature_exists:
            ModularFeature_Remove(USERINPUT_FeatureChoice, REPO_PATH, LoaderWidget, USERINPUT_SafeUpdate)
        ModularFeature_Add(USERINPUT_FeatureChoice, REPO_PATH, special_inputs, LoaderWidget, USERINPUT_SafeUpdate)
        LoaderWidget.markdown("Feature Added!")

        # Save PyVen Metadata for the repo after adding the feature
        FEATURES_DATA = LoadPyVenFeaturesMetadata(REPO_PATH)
        FEATURES_DATA["added_features"][USERINPUT_FeatureChoiceName] = {
            "name": USERINPUT_FeatureChoiceName,
            "special": special_inputs
        }
        SavePyVenFeaturesMetadata(REPO_PATH, FEATURES_DATA)
        feature_exists = True
        button_name = "Update"
        bcol1.button(button_name + " Feature", key="BU")
        USERINPUT_RebuildPyVenData = True
    
    if feature_exists:
        if bcol2.button("Remove Feature"):
            LoaderWidget = st.empty()
            ModularFeature_Remove(USERINPUT_FeatureChoice, REPO_PATH, LoaderWidget, USERINPUT_SafeUpdate)

            # Save PyVen Metadata for the repo after removing the feature
            FEATURES_DATA = LoadPyVenFeaturesMetadata(REPO_PATH)
            FEATURES_DATA["added_features"].pop(USERINPUT_FeatureChoiceName)
            SavePyVenFeaturesMetadata(REPO_PATH, FEATURES_DATA)
            feature_exists = False
            button_name = "Add"
            bcol1.button(button_name + " Feature", key="BA2")
            bcol2.markdown("")
            USERINPUT_RebuildPyVenData = True

    if USERINPUT_RebuildPyVenData:
        RebuildModules(REPO_PATH, PROGRESS_OBJ=st.sidebar.progress(0.0))
        UpdateRepoBasicDetails(REPO_PATH, REPO_NAME)
        st.sidebar.markdown("Rebuilt PyVen Data for " + REPO_NAME + "!")

def settings():
    global CACHE

    # Title
    st.header("Settings")

    LoadCache()

    # Load Inputs
    st.markdown("## Git Repo Paths")
    USERINPUT_GitRepoPathsText = st.text_area("Enter Git Repo Search Dirs", "\n".join(CACHE["PATHS_PARENT_GIT"]))

    # Process Inputs
    USERINPUT_GitRepoPaths = USERINPUT_GitRepoPathsText.split("\n")

    # Display Outputs
    if st.button("Save"):
        CACHE["PATHS_PARENT_GIT"] = USERINPUT_GitRepoPaths
        CACHE["GIT_REPOS"] = UI_LoadRepos(CACHE["PATHS_PARENT_GIT"])
        SaveCache()
        st.markdown("Saved Settings!")

    
#############################################################################################################################
# Driver Code
if __name__ == "__main__":
    main()