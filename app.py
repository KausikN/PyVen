"""
Stream lit GUI for hosting PyVen
"""

# Imports
import os
import cv2
import pickle
import functools
import numpy as np
from pkg_resources import require
import streamlit as st
import json

import PyVen
import ModularFeatures

# Main Vars
config = json.load(open('./StreamLitGUI/UIConfig.json', 'r'))

# Main Functions
def main():
    # Create Sidebar
    selected_box = st.sidebar.selectbox(
    'Choose one of the following',
        tuple(
            [config['PROJECT_NAME']] + 
            config['PROJECT_MODES']
        )
    )
    
    if selected_box == config['PROJECT_NAME']:
        HomePage()
    else:
        correspondingFuncName = selected_box.replace(' ', '_').lower()
        if correspondingFuncName in globals().keys():
            globals()[correspondingFuncName]()
 

def HomePage():
    st.title(config['PROJECT_NAME'])
    st.markdown('Github Repo: ' + "[" + config['PROJECT_LINK'] + "](" + config['PROJECT_LINK'] + ")")
    st.markdown(config['PROJECT_DESC'])

    # st.write(open(config['PROJECT_README'], 'r').read())

#############################################################################################################################
# Repo Based Vars
DEFAULT_SAVEPATH_JSON = 'DependencyData/Modules.json'
FEATURES_PATH = 'ModularFeaturesData/'
CACHE_PATH = "StreamLitGUI/CacheData/Cache.json"

DEFAULT_FEATURE_NAME_PYVENSTARTER = "PyVenStarter"

# Util Vars
CACHE = {}
FEATURES = {}

# Util Functions
def Hex_to_RGB(val):
    val = val.lstrip('#')
    lv = len(val)
    return tuple(int(val[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def RGB_to_Hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

def JoinPath(*ops):
    return os.path.join(*ops).replace("\\", "/")

def GetNames(data):
    names = []
    for d in data:
        names.append(d["name"])
    return names

def GetNames_Dict(data):
    names = []
    keys = []
    for dk in data.keys():
        d = data[dk]
        keys.append(dk)
        names.append(d["name"])
    return names, keys

def LoadCache():
    global CACHE
    CACHE = json.load(open(CACHE_PATH, 'r'))

def SaveCache():
    global CACHE
    json.dump(CACHE, open(CACHE_PATH, 'w'), indent=4)

def LoadFeatures():
    global FEATURES
    for f in os.listdir(FEATURES_PATH):
        FEATURES[f] = JoinPath(FEATURES_PATH, f)

def LoadPyVenFeaturesMetadata(repo_path):
    FEATURES_DATA = json.load(open(JoinPath(repo_path, ".pyven/features.json"), 'r'))
    return FEATURES_DATA

def SavePyVenFeaturesMetadata(repo_path, FEATURES_DATA):
    json.dump(FEATURES_DATA, open(JoinPath(repo_path, ".pyven/features.json"), 'w'), indent=4)

def SavePyVenModulesMetadata(repo_path, MODULES_DATA):
    json.dump(MODULES_DATA, open(JoinPath(repo_path, ".pyven/modules.json"), 'w'), indent=4)

# Main Functions
def RebuildModules(REPO_PATH):
    Modules = PyVen.Repo_FindModules(REPO_PATH)
    SavePyVenModulesMetadata(REPO_PATH, Modules)

def UpdateRepoBasicDetails(REPO_PATH, REPO_NAME):
    BasicInfo = json.load(open(JoinPath(REPO_PATH, ".pyven/basic_info.json"), 'r'))
    BasicInfo["repo_name"] = REPO_NAME
    requirements = []
    if "requirements.txt" in os.listdir(REPO_PATH):
        requirements = [line.strip() for line in open(JoinPath(REPO_PATH, "requirements.txt"), 'r').readlines()]
    BasicInfo["requirements"] = requirements
    json.dump(BasicInfo, open(JoinPath(REPO_PATH, ".pyven/basic_info.json"), 'w'), indent=4)

# UI Functions
def UI_LoadRepos(parentPaths):
    pathCount = len(parentPaths)

    LoaderText = st.empty()
    REPO_PATHS = []
    i = 0
    for parentPath in parentPaths:
        repoPaths = PyVen.GetAllLocalRepos(parentPath)
        REPO_PATHS.extend(repoPaths)
        i += 1
        LoaderText.markdown("[" + str(i) + " / " + str(pathCount) + "] Loaded " + parentPath)
    REPO_PATHS = list(set(REPO_PATHS))
    LoaderText.markdown("Loaded " + str(len(REPO_PATHS)) + " repos.")
    REPO_DATAS = [{
        "name": os.path.split(repoPath.rstrip("/"))[-1],
        "path": repoPath
    } for repoPath in REPO_PATHS]
    return REPO_DATAS

def UI_DisplayRepoTreeData(repo):
    st.markdown("## " + repo["name"])
    st.markdown("<a href=" + repo["repoLink"] + ">" + repo["repoLink"] + "</a>", unsafe_allow_html=True)
    st.markdown(repo["localPath"])

    Modules_Names, Modules_Keys = GetNames_Dict(repo["modules"])
    st.markdown("## Modules")
    USERINPUT_ModuleName = st.selectbox("Select Module", ["Select Module"] + Modules_Names)
    if USERINPUT_ModuleName == "Select Module": return
    USEINPUT_Module = repo["modules"][Modules_Keys[Modules_Names.index(USERINPUT_ModuleName)]]
    st.markdown("### " + USEINPUT_Module["name"])
    detailSizeRatio = [1, 3]
    col1, col2 = st.beta_columns(detailSizeRatio)
    col1.markdown("Module Type:")
    col2.markdown(USEINPUT_Module["type"])
    col1, col2 = st.beta_columns(detailSizeRatio)
    col1.markdown("Module Heirarchy:")
    col2.markdown('.'.join(USEINPUT_Module["subDir"].split("/") + [USEINPUT_Module["name"]]), unsafe_allow_html=True)
    if USEINPUT_Module["type"] == "local":
        col1, col2 = st.beta_columns(detailSizeRatio)
        col1.markdown("File Link:")
        col2.markdown("<a href=" + USEINPUT_Module["link"] + ">" + USEINPUT_Module["link"] + "</a>", unsafe_allow_html=True)
        col1, col2 = st.beta_columns(detailSizeRatio)
        col1.markdown("Dependencies:")
        deps = [repo["modules"][key]["name"] for key in USEINPUT_Module["dependencies"]]
        col2.markdown(', '.join(deps))

def UI_GetFeatureParams(feature_path, defaults=None, nCols=3):
    includes = json.load(open(JoinPath(feature_path, "includes.json"), 'r'))
    specialInputs = {"choiceBased": {}, "checkBased": {}}
    # Choice Based
    choiceBasedData = includes["special"]["choiceBased"]
    nChoiceParams = len(choiceBasedData.keys())
    choiceBasedData_Labels = list(choiceBasedData.keys())
    params_done = 0
    while(params_done < nChoiceParams):
        params_todo = min(nCols, nChoiceParams-params_done)
        cols = st.beta_columns(params_todo)
        for i in range(params_todo):
            choiceDataKey = choiceBasedData_Labels[params_done + i]
            choiceNames = GetNames(choiceBasedData[choiceDataKey]["choices"])
            defaultVal = 0 if defaults is None else defaults["choiceBased"][choiceDataKey]
            inp = cols[i].selectbox(choiceBasedData[choiceDataKey]["label"], choiceNames, index=defaultVal)
            inp_index = choiceNames.index(inp)
            specialInputs["choiceBased"][choiceDataKey] = inp_index
        params_done += params_todo
    # Check Based
    checkBasedData = includes["special"]["checkBased"]
    nCheckParams = len(checkBasedData.keys())
    checkBasedData_Labels = list(checkBasedData.keys())
    params_done = 0
    while(params_done < nCheckParams):
        params_todo = min(nCols, nCheckParams-params_done)
        cols = st.beta_columns(params_todo)
        for i in range(params_todo):
            checkDataKey = checkBasedData_Labels[params_done + i]
            defaultVal = False if defaults is None else defaults["checkBased"][checkDataKey]
            inp = st.checkbox(checkBasedData[checkDataKey]["label"], defaultVal)
            specialInputs["checkBased"][checkDataKey] = inp
        params_done += params_todo
    
    return specialInputs

def UI_CheckPyVenInit(REPO_PATH, REPO_NAME):
    if ".pyven" not in os.listdir(REPO_PATH):
        InitButton = st.empty()
        if InitButton.button("Initialise PyVen for the Repo"):
            # Add PyVen Starter Feature
            USERINPUT_FeatureChoice = FEATURES[DEFAULT_FEATURE_NAME_PYVENSTARTER]
            LoaderWidget = st.empty()
            ModularFeatures.ModularFeature_Add(USERINPUT_FeatureChoice, REPO_PATH, {"choiceBased": {}, "checkBased": {}}, LoaderWidget)

            # Update Modules in .pyven
            RebuildModules(REPO_PATH)

            # Update basic_info.json
            UpdateRepoBasicDetails(REPO_PATH, REPO_NAME)
            
            LoaderWidget.markdown("Repo initialised with PyVen!")
            InitButton.markdown("")
            return True
        else:
            return False
    return True

def UI_SearchModePrune(REPO_DATAS, REPO_NAMES):
    global FEATURES

    USERINPUT_SearchMode = st.selectbox("Search Mode", ["Search by Repo Name", "Search by Added Features"])
    if USERINPUT_SearchMode == "Search by Repo Name":
        return REPO_DATAS, REPO_NAMES
    elif USERINPUT_SearchMode == "Search by Added Features":
        USERINPUT_RequiredFeatures = st.multiselect("Features", list(FEATURES.keys()))
        if len(USERINPUT_RequiredFeatures) == 0: return REPO_DATAS, REPO_NAMES
        REPO_DATAS_PRUNED, REPO_NAMES_PRUNED = [], []
        for repo in REPO_DATAS:
            repo_path = repo["path"]
            if ".pyven" not in os.listdir(repo_path): # Repo not initialised with pyven
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

    # Title
    st.header("Analyse Local Repo")

    LoadCache()
    LoadFeatures()
    REPO_NAMES = GetNames(CACHE["GIT_REPOS"])
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
    REPO_TREE = PyVen.Repo_FindModules(REPO_PATH)

    # Display Outputs
    UI_DisplayRepoTreeData(REPO_TREE)

    # Check if PyVen Features Added
    st.markdown("## Features Added")
    ADDED_FEATURES = ModularFeatures.ModularFeature_Check(REPO_PATH)
    if ADDED_FEATURES is None:
        st.markdown("Repo not initialsed with PyVen.")
    else:
        USERINPUT_AddedFeaturesChoice = st.selectbox("Added Features", ADDED_FEATURES)

    if USERINPUT_RebuildPyVenData:
        RebuildModules(REPO_PATH)
        UpdateRepoBasicDetails(REPO_PATH, REPO_NAME)
        st.sidebar.markdown("Rebuilt PyVen Data for " + REPO_NAME + "!")

def edit_repo_features():
    global FEATURES

    # Title
    st.header("Edit Repo Features")

    LoadCache()
    LoadFeatures()
    REPO_NAMES = GetNames(CACHE["GIT_REPOS"])
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

    features_pyven_repo_path = JoinPath(REPO_PATH, ".pyven/features.json")
    added_features_data = json.load(open(features_pyven_repo_path, 'r'))["added_features"]
    ButtonName = "Add"
    featureExists = False
    specialInputs_Default = None
    if USERINPUT_FeatureChoiceName not in added_features_data.keys():
        st.markdown("Feature " + USERINPUT_FeatureChoiceName + " not yet added to " + REPO_NAME + ".")
    else:
        st.markdown("Feature " + USERINPUT_FeatureChoiceName + " already added in " + REPO_NAME + ".")
        ButtonName = "Update"
        featureExists = True
        # specialInputs_Default = added_features_data[USERINPUT_FeatureChoiceName]["special"] # Commented as this messes up the UI

    specialInputs = UI_GetFeatureParams(USERINPUT_FeatureChoice, specialInputs_Default)

    # Process Inputs
    col1, col2 = st.beta_columns(2)
    bcol1 = col1.empty()
    bcol2 = col2.empty()
    if bcol1.button(ButtonName + " Feature", key="BA1"):
        LoaderWidget = st.empty()
        if featureExists:
            ModularFeatures.ModularFeature_Remove(USERINPUT_FeatureChoice, REPO_PATH, LoaderWidget, USERINPUT_SafeUpdate)
        ModularFeatures.ModularFeature_Add(USERINPUT_FeatureChoice, REPO_PATH, specialInputs, LoaderWidget, USERINPUT_SafeUpdate)
        LoaderWidget.markdown("Feature Added!")

        # Save PyVen Metadata for the repo after adding the feature
        FEATURES_DATA = LoadPyVenFeaturesMetadata(REPO_PATH)
        FEATURES_DATA["added_features"][USERINPUT_FeatureChoiceName] = {
            "name": USERINPUT_FeatureChoiceName,
            "special": specialInputs
        }
        SavePyVenFeaturesMetadata(REPO_PATH, FEATURES_DATA)
        featureExists = True
        ButtonName = "Update"
        bcol1.button(ButtonName + " Feature", key="BU")
        USERINPUT_RebuildPyVenData = True
    
    if featureExists:
        if bcol2.button("Remove Feature"):
            LoaderWidget = st.empty()
            ModularFeatures.ModularFeature_Remove(USERINPUT_FeatureChoice, REPO_PATH, LoaderWidget, USERINPUT_SafeUpdate)

            # Save PyVen Metadata for the repo after removing the feature
            FEATURES_DATA = LoadPyVenFeaturesMetadata(REPO_PATH)
            FEATURES_DATA["added_features"].pop(USERINPUT_FeatureChoiceName)
            SavePyVenFeaturesMetadata(REPO_PATH, FEATURES_DATA)
            featureExists = False
            ButtonName = "Add"
            bcol1.button(ButtonName + " Feature", key="BA2")
            bcol2.markdown("")
            USERINPUT_RebuildPyVenData = True

    if USERINPUT_RebuildPyVenData:
        RebuildModules(REPO_PATH)
        UpdateRepoBasicDetails(REPO_PATH, REPO_NAME)
        print("Here")
        st.sidebar.markdown("Rebuilt PyVen Data for " + REPO_NAME + "!")


def settings():
    global CACHE

    # Title
    st.header("Settings")

    LoadCache()

    # Load Inputs
    st.markdown("## Git Repo Paths")
    USERINPUT_GitRepoPathsText = st.text_area("Enter Git Repo Search Dirs", '\n'.join(CACHE["PATHS_PARENT_GIT"]))

    # Process Inputs
    USERINPUT_GitRepoPaths = USERINPUT_GitRepoPathsText.split('\n')

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