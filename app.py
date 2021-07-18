"""
Stream lit GUI for hosting PyVen
"""

# Imports
import os
import cv2
import pickle
import functools
import numpy as np
import streamlit as st
import json

import PyVen
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
CACHE_PATH = "StreamLitGUI/CacheData/Cache.json"

# Util Vars
CACHE = {}

# Util Functions
def Hex_to_RGB(val):
    val = val.lstrip('#')
    lv = len(val)
    return tuple(int(val[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

def RGB_to_Hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(rgb[0], rgb[1], rgb[2])

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

# Main Functions


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

# Repo Based Functions
def analyse_repo():
    # Title
    st.header("Analyse Local Repo")

    LoadCache()
    REPO_NAMES = GetNames(CACHE["GIT_REPOS"])
    REPO_DATAS = CACHE["GIT_REPOS"]

    # Load Inputs
    USERINPUT_RepoChoiceName = st.selectbox("Select Repo", ["Select Repo"] + REPO_NAMES)
    if USERINPUT_RepoChoiceName == "Select Repo": return
    USERINPUT_RepoChoice = REPO_DATAS[REPO_NAMES.index(USERINPUT_RepoChoiceName)]

    # Process Inputs
    # Load Repo
    REPO_PATH = USERINPUT_RepoChoice["path"]
    REPO_NAME = USERINPUT_RepoChoice["name"]
    REPO_TREE = PyVen.Repo_GenerateTree(REPO_PATH)

    # Display Outputs
    UI_DisplayRepoTreeData(REPO_TREE)

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