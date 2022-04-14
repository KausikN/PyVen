'''
A python importing and packaging tool similar to Maven for Java
'''

# Imports
import os
import json
import importlib
import functools
import ast
from tqdm import tqdm
import multiprocessing

# Main Functions
def SaveData(data, path):
    json.dump(data, open(path, "w"), indent=4)

def GetModulePath(moduleData, absolute=True):
    if absolute:
        return os.path.join(moduleData["parentDir"], moduleData["subDir"], moduleData["name"] + ".py").replace("\\", "/")
    else:
        return os.path.join(moduleData["subDir"], moduleData["name"] + ".py").replace("\\", "/")

def GetCompressedDep(dep):
    depCleaned = {
        "name": dep["name"],
        "type": dep["type"],
        "parentDir": dep["parentDir"],
        "subDir": dep["subDir"],
        "dependencies": dep["dependencies"]
    }
    return depCleaned

def UpdateUniqueDependencies(uD, newDeps):
    uD_Updated = dict(uD)
    for depKey in newDeps.keys():
        dep = newDeps[depKey]
        subModPath = GetModulePath(dep)
        if subModPath not in uD_Updated.keys():
            uD_Updated[subModPath] = GetCompressedDep(dep)
    return uD_Updated

def CheckPipModule_Internal(MODULE_PRESENT, moduleName, package):
    try:
        mod_spec_pkg = importlib.util.find_spec(moduleName, package=package)
        if (mod_spec_pkg is not None): MODULE_PRESENT.value = True
        mod_spec_direct = importlib.util.find_spec(package + "." + moduleName, package="")
        MODULE_PRESENT.value = (mod_spec_direct is not None)
    except:
        MODULE_PRESENT.value = False

def CheckIfPipModule(moduleName, package):
    MODULE_PRESENT = multiprocessing.Value("b", True)
    p = multiprocessing.Process(target=functools.partial(CheckPipModule_Internal, MODULE_PRESENT, moduleName, package))
    p.start()
    p.join(timeout=2.5)
    if p.is_alive():
        p.kill()
        p.join()
    return bool(MODULE_PRESENT.value)

def SplitPipModule(moduleStr):
    newModuleName = None
    newModuleParent = None
    moduleHeirarchy = moduleStr.split(".")
    while len(moduleHeirarchy) > 0:
        curModuleName = moduleHeirarchy[-1]
        curModuleParent = ".".join(moduleHeirarchy[:-1])
        if CheckIfPipModule(curModuleName, curModuleParent):
            newModuleName = curModuleName
            newModuleParent = curModuleParent
            break
        moduleHeirarchy = moduleHeirarchy[:-1]
    return newModuleName, newModuleParent

def GetAllLocalRepos(parent_path):
    repo_list = []
    for repo in os.listdir(parent_path):
        if os.path.isdir(os.path.join(parent_path, repo)): # Check if dir
            # Check if git repo (shud have .git folder)
            if ".git" in os.listdir(os.path.join(parent_path, repo)):
                repo_list.append(os.path.join(parent_path, repo).replace("\\", "/"))
            # Else recurse inside the folder to check for git repos inside it
            else:
                repo_list.extend(GetAllLocalRepos(os.path.join(parent_path, repo)))
    return repo_list
            

### Imports Parsers ######################################################################################################
def ParseImports_Python_Regex(code_path):
    '''
    ParseImports_Python_Regex(path) -> list<str>
    Parses all imports in a python file using Regex
    '''

    if not os.path.exists(code_path): return []

    codeDir = os.path.dirname(code_path).replace("\\", "/")

    code = open(code_path, 'r', encoding="utf8").read()
    code_lines = code.split('\n')

    imports = []
    inMultiLineComment = None
    for line in code_lines:
        line = line.strip()
        # Check for multi line comments
        if inMultiLineComment is None:
            if line.startswith('"""'):
                inMultiLineComment = '"""'
            elif line.startswith("'''"):       
                inMultiLineComment = "'''"
        if inMultiLineComment is not None:
            if line.endswith(inMultiLineComment):
                inMultiLineComment = None
            continue
        # Check Comments
        if line.startswith('#'):
            continue

        # Check for imports
        # Imports can be
        # => import {module1},{module2},{modulen}
        if line.startswith('import '):
            importsCode = line[7:].strip() # Remove import keyword
            lineImports = importsCode.split(",") # Split into list of modules

            lineImports_Cleaned = []
            for imp in lineImports:
                asIndex = imp.find(" as ") # Check for 'as' keyword
                if asIndex != -1: imp = imp[:asIndex] # Remove string after as key word
                imp = imp.strip()
                importData = {
                    "parentDir": codeDir,
                    "subDir": "",
                    "name": imp
                }
                lineImports_Cleaned.append(importData)

            imports.extend(lineImports_Cleaned)

        # => from {dir1.dir2.dirn} import {module}
        elif line.startswith('from '):
            importsDirsCode = line[5:].strip() # Remove from keyword
            dirImportsList = importsDirsCode.split(" import ") # Split into list of modules imported from a dirctory
            importDir = dirImportsList[0].strip().replace(".", "/") # Get directory as path

            lineImports_Cleaned = []
            importsCode = dirImportsList[1].strip()
            if importsCode == "*" or importDir.startswith("/"):
                moduleSplitup = importDir.strip("/").split("/")
                moduleName = moduleSplitup[-1]
                importDir = "/".join(moduleSplitup[:-1])
                importData = {
                    "parentDir": codeDir,
                    "subDir": importDir,
                    "name": moduleName
                }
                lineImports_Cleaned.append(importData)
            else:
                # Check if importing functions inside a module - if so only import the main module
                importDir = importDir.rstrip("/")
                newImportName, newImportPackage = SplitPipModule(importDir.replace("/", "."))
                if newImportName is not None:
                    importData = {
                        "parentDir": codeDir,
                        "subDir": newImportPackage.replace(".", "/"),
                        "name": newImportName
                    }
                    lineImports_Cleaned.append(importData)
                elif os.path.exists(os.path.join(codeDir, importDir + ".py")):
                    newImportSplit = os.path.split(importDir)
                    importData = {
                        "parentDir": codeDir,
                        "subDir": "/".join(newImportSplit[:-1]),
                        "name": newImportSplit[-1]
                    }
                    lineImports_Cleaned.append(importData)
                else:
                    lineImports = importsCode.split(",") # Split into list of modules
                    for imp in lineImports:
                        asIndex = imp.find(" as ") # Check for 'as' keyword
                        if asIndex != -1: imp = imp[:asIndex] # Remove string after as key word
                        imp = imp.strip()

                        importData = {
                            "parentDir": codeDir,
                            "subDir": importDir,
                            "name": imp
                        }
                        lineImports_Cleaned.append(importData)

            imports.extend(lineImports_Cleaned)

    return imports

def ParseImports_Python(code_path):
    '''
    ParseImports_Python(path) -> list<str>
    Parses all imports in a python file using ast module
    '''

    if not os.path.exists(code_path): return []
    codeDir = os.path.dirname(code_path).replace("\\", "/")
    code = open(code_path, 'r', encoding="utf8").read()

    CodeModule = ast.parse(code)
    # functions = [x for x in CodeModule.body if isinstance(x, ast.FunctionDef)]

    imports = []
    Imports = [x for x in CodeModule.body if isinstance(x, ast.Import)]
    FromImports = [x for x in CodeModule.body if isinstance(x, ast.ImportFrom)]
    for impG in Imports:
        impsDicts = []
        for imp in impG.names:
            name = imp.name.split(".")[-1]
            module = imp.name.rstrip(name).rstrip(".")
            impData = {
                "parentDir": codeDir,
                "subDir": "/".join(module.split(".")),
                "name": name
            }
            impsDicts.append(impData)
        imports.extend(impsDicts)
    for impG in FromImports:
        impsDicts = []
        for imp in impG.names:
            name = imp.name.split(".")[-1]
            module = imp.name.rstrip(name).rstrip(".")
            if impG.module is not None:
                module = ".".join([module, imp.name.rstrip(name).rstrip(".")]).rstrip(".")
            impData = {
                "parentDir": codeDir,
                "subDir": "/".join(module.split(".")),
                "name": name
            }
            impsDicts.append(impData)
        imports.extend(impsDicts)
        
    return imports

##########################################################################################################################

### BASIC DEPENDENCY TREE ################################################################################################
def DependencyTree_Basic_Python(code_path, level=0, display=False):
    padText = "----" * level

    codeDir = os.path.dirname(code_path)
    moduleName = os.path.splitext(os.path.basename(code_path))[0]
    moduleType = "local" # local file

    if display: print(padText + "Module: " + moduleName)

    Imports = ParseImports_Python(code_path)
    ModuleDependencyTree = []
    i, impCount = 0, len(Imports)
    for imp in Imports:
        subModulePath = GetModulePath(imp)
        # Check if submodule is inbuilt (through pip install) or local => If file exists == local else inbuilt
        subModuleType = "local" if os.path.exists(subModulePath) else ("inbuilt" if CheckIfPipModule(imp["name"], imp["subDir"].replace("/", ".")) else "missing")
        
        i += 1
        if display: print(padText + "[" + str(i) + " / " + str(impCount) + "]" + "|" + subModuleType + "|: " + imp["name"])

        subModuleDependencyTree = []
        if subModuleType == "local":
            subModuleDependencyTree = DependencyTree_Basic_Python(subModulePath, level=level+1, display=display)['dependencies']
        elif subModuleType == "inbuilt":
            imp["parentDir"] = "" # No Parent Dir for inbuilt modules

        subModule = {
            "name": imp["name"],
            "type": subModuleType,
            "parentDir": imp["parentDir"],
            "subDir": imp["subDir"],
            "dependencies": subModuleDependencyTree
        }
        ModuleDependencyTree.append(subModule)

    Module = {
        "name": moduleName,
        "type": moduleType,
        "parentDir": codeDir,
        "subDir": "",
        "dependencies": ModuleDependencyTree
    }
    return Module

def DependencyTree_Compress(Module, level=0, display=False):
    padText = "----" * level
    if display: print(padText + "Module: " + Module["name"])

    ModuleDependencyTree = Module["dependencies"]
    uniqueDependencies = {}
    dependencyKeys = []
    i, depCount = 0, len(ModuleDependencyTree)
    for dep in ModuleDependencyTree:
        i += 1
        if display: print(padText + "[" + str(i) + " / " + str(depCount) + "]" + "|" + dep["type"] + "|: " + dep["name"])

        subModPath = GetModulePath(dep)
        if subModPath not in uniqueDependencies.keys():
            depCleaned = DependencyTree_Compress(dep, level=level+1, display=display)
            uniqueDependencies[subModPath] = GetCompressedDep(depCleaned)
            uniqueDependencies = UpdateUniqueDependencies(uniqueDependencies, depCleaned["dependencyModules"])

        dependencyKeys.append(subModPath)

    Module_Compressed = {
        "name": Module["name"],
        "type": Module["type"],
        "parentDir": Module["parentDir"],
        "subDir": Module["subDir"],
        "dependencies": dependencyKeys,
        "dependencyModules": uniqueDependencies
    }
    
    return Module_Compressed
##########################################################################################################################

### COMPRESSED DEPENDENCY TREE ###########################################################################################
def DependencyTree_Compressed_Python(code_path, level=0, display=False):
    padText = "----" * level

    codeDir = os.path.dirname(code_path)
    moduleName = os.path.splitext(os.path.basename(code_path))[0]
    moduleType = "local" # local file

    if display: print(padText + "Module: " + moduleName)

    Imports = ParseImports_Python(code_path)
    uniqueDependencies = {}
    dependencyKeys = []
    i, impCount = 0, len(Imports)
    for imp in Imports:
        subModulePath = GetModulePath(imp)
        # Check if submodule is inbuilt (through pip install) or local => If file exists == local else inbuilt
        subModuleType = "local" if os.path.exists(subModulePath) else ("inbuilt" if CheckIfPipModule(imp["name"], imp["subDir"].replace("/", ".")) else "missing")
        if subModuleType == "inbuilt":
            imp["parentDir"] = ""
            subModulePath = GetModulePath(imp)
        
        i += 1
        if display: print(padText + "[" + str(i) + " / " + str(impCount) + "]" + "|" + subModuleType + "|: " + imp["name"])

        if subModulePath not in uniqueDependencies.keys():
            depCleaned = imp
            if subModuleType == "local":
                depCleaned = DependencyTree_Compressed_Python(subModulePath, level=level+1, display=display)
            else:
                depCleaned["type"] = subModuleType
                if subModuleType == "inbuilt":
                    depCleaned["parentDir"] = "" # No Parent Dir for inbuilt modules
                depCleaned["dependencies"] = [] # No dependencies for inbuilt modules
                depCleaned["dependencyModules"] = {}
            depCleaned["subDir"] = imp["subDir"]
            uniqueDependencies[subModulePath] = GetCompressedDep(depCleaned)
            uniqueDependencies = UpdateUniqueDependencies(uniqueDependencies, depCleaned["dependencyModules"])
        dependencyKeys.append(subModulePath)

    Module = {
        "name": moduleName,
        "type": moduleType,
        "parentDir": codeDir,
        "subDir": "",
        "dependencies": dependencyKeys,
        "dependencyModules": uniqueDependencies
    }
    return Module
##########################################################################################################################

### REPO LEVEL PYVEN #####################################################################################################
def Repo_FindModules(repo_path, userName="KausikN", display=False, progressObj=None):
    repoName = repo_path.rstrip("/").split("/")[-1]

    CodeFiles = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                CodeFiles.append(os.path.join(root, file))
    
    uniqueModules = {}
    importedModulePaths = []
    i, fCount = 0, len(CodeFiles)
    for f in CodeFiles:
        i += 1
        if display: print("[" + str(i) + " / " + str(fCount) + "]" + ": " + f)

        subDir = os.path.split(f)[0][len(repo_path):].replace("\\", "/").strip("/")
        moduleName = os.path.splitext(os.path.basename(f))[0]
        moduleType = "local" # local as file exists

        Imports = ParseImports_Python(f)
        ImportPaths = []
        for imp in Imports:
            absPath = GetModulePath(imp, absolute=True)
            path = GetModulePath(imp, absolute=False)
            if os.path.exists(absPath): 
                path = os.path.join(subDir, path).replace("\\", "/")
            ImportPaths.append(path)

        moduleLink = "https://github.com/" + userName + "/" + repoName + "/blob/master/" + subDir + "/" + moduleName + ".py"
        if subDir == "":
            moduleLink = "https://github.com/" + userName + "/" + repoName + "/blob/master/" + moduleName + ".py"
        Module = {
            "name": moduleName,
            "type": moduleType,
            "link": moduleLink,
            "parentDir": repo_path,
            "subDir": subDir,
            "dependencies": ImportPaths,
        }
        uniqueModules[GetModulePath(Module, absolute=False)] = Module
        importedModulePaths.extend(ImportPaths)

    # Check if all imported modules are local or else mark as inbuilt
    importedModulePaths = list(set(importedModulePaths)) # Remove Duplicates
    i = 0
    for path in tqdm(importedModulePaths):
        if path not in uniqueModules.keys():
            subDir = os.path.split(path)[0].replace("\\", "/").strip("/")
            moduleName = os.path.splitext(os.path.basename(path))[0]
            moduleType = "inbuilt" if CheckIfPipModule(moduleName, subDir.replace("/", ".")) else "missing"
            parentDir = repo_path if moduleType == "inbuilt" else ""
            Module = {
                "name": moduleName,
                "type": moduleType,
                "link": "", # No Link for inbuilt modules
                "parentDir": parentDir,
                "subDir": subDir,
                "dependencies": [],
            }
            uniqueModules[path] = Module
        i += 1
        if progressObj is not None: progressObj.progress(i / len(importedModulePaths))

    Repo = {
        "name": repoName,
        "repoLink": "https://github.com/" + userName + "/" + repoName,
        "localPath": repo_path,
        "modules": uniqueModules
    }

    return Repo
##########################################################################################################################

# Driver Code
# # Params
# userName = "KausikN"
# repoPath = "E:/Github Codes and Projects/Projects/VidFX/"
# savePath = "DependencyData/PyVenTree_VidFX.json"
# # Params

# # print(CheckIfPipModule("semantic_segmentation", "pixellib.semantic"))
# # print(CheckIfPipModule("semantic", "pixellib"))
# # print(CheckIfPipModule("pixellib", ""))
# # quit()

# # RunCode
# print(repoPath)
# print("Computing Repo Tree...")
# Repo = Repo_FindModules(repoPath, userName=userName, display=True)

# SaveData(Repo, savePath)