"""
A python importing and packaging tool similar to Maven for Java
"""

# Imports
import os
import json
import importlib
import functools
import ast
import multiprocessing
from tqdm import tqdm

# Main Functions
# Module Functions
def Module_CleanModuleDirs(parent_dir, import_dir):
    '''
    Module - Clean Parent Dir and Import Dir (Check and resolve relative paths)
    '''
    if import_dir.startswith("/"):
        rel_count = len(import_dir) - len(import_dir.lstrip("/")) - 1
        if rel_count > 0: parent_dir = "/".join(parent_dir.split("/")[:-rel_count])
        import_dir = import_dir.lstrip("/")
    return parent_dir, import_dir

def Module_GetPath(module_data, absolute=True):
    '''
    Module - Get Module Path
    '''
    if absolute:
        return os.path.join(module_data["parent_dir"], module_data["sub_dir"], module_data["name"] + ".py").replace("\\", "/")
    else:
        return os.path.join(module_data["sub_dir"], module_data["name"] + ".py").replace("\\", "/")

def Dep_Compress(dep):
    '''
    Dependency - Compress Data
    '''
    return {
        "name": dep["name"],
        "type": dep["type"],
        "parent_dir": dep["parent_dir"],
        "sub_dir": dep["sub_dir"],
        "dependencies": dep["dependencies"]
    }

def Dep_UpdateDeps(deps, new_deps):
    '''
    Dependency - Update Dependencies (with new dependencies)
    '''
    # Copy Dependencies
    deps_updated = dict(deps)
    # Update Dependencies with new dependencies
    for depKey in new_deps.keys():
        dep = new_deps[depKey]
        sub_mod_path = Module_GetPath(dep)
        if sub_mod_path not in deps_updated.keys(): deps_updated[sub_mod_path] = Dep_Compress(dep)
    return deps_updated

# Pip Functions
def Pip_CheckModule_ProcessFunc(MODULE_PRESENT, module_name, package):
    '''
    Pip - Check Module (Process Func - for multiprocessing)
    '''
    try:
        # Check if module is present in pip in local environment under the given package
        ## Eg: package = "tensorflow", module_name = "keras"
        mod_spec_pkg = importlib.util.find_spec(module_name, package=package)
        if (mod_spec_pkg is not None): MODULE_PRESENT.value = True
        else:
            # Check if module is present in pip in local environment directly
            ## Eg: package = "", module_name = "tensorflow"
            mod_spec_direct = importlib.util.find_spec(package + "." + module_name, package="")
            MODULE_PRESENT.value = (mod_spec_direct is not None)
    except:
        MODULE_PRESENT.value = False

def Pip_CheckModule(module_name, package, timeout=5.0):
    '''
    Pip - Check Module
    '''
    # Init
    MODULE_PRESENT = multiprocessing.Value("b", False)
    # Call Check Pip Module Process
    p = multiprocessing.Process(target=functools.partial(Pip_CheckModule_ProcessFunc, MODULE_PRESENT, module_name, package))
    p.start()
    p.join(timeout=timeout)
    # Kill Process if not completed
    if p.is_alive():
        p.kill()
        p.join()
    return bool(MODULE_PRESENT.value)

def Pip_SplitModule(module_str):
    '''
    Pip - Split Module String to get the main module name and the parent package
    '''
    # Init
    module_name = None
    module_parent = None
    module_heirarchy = module_str.split(".")
    # Loop through the heirarchy from right to left till a module is found with its parent package
    ## Eg: module_str = "tensorflow.keras.layers.Dense"
    ## Here, "Dense" is a class and not a module, so we get False for Pip_CheckModule
    ## Similarly, "layers" is also not a module, so we get False for Pip_CheckModule
    ## Next, "keras" is a module, so we get True for Pip_CheckModule with package = "tensorflow"
    ## Thus, we get module_name = "keras" and module_parent = "tensorflow"
    while len(module_heirarchy) > 0:
        cur_module_name = module_heirarchy[-1]
        cur_module_parent = ".".join(module_heirarchy[:-1])
        if Pip_CheckModule(cur_module_name, cur_module_parent):
            module_name = cur_module_name
            module_parent = cur_module_parent
            break
        module_heirarchy = module_heirarchy[:-1]
    return module_name, module_parent

# Repo Functions
def Repo_GetLocalRepos(parent_path):
    '''
    Repo - Get Local Repos
    '''
    # Init
    parent_path = parent_path.replace("\\", "/")
    repo_list = []
    # Loop through all files and folders in the parent path
    for repo in os.listdir(parent_path):
        if os.path.isdir(os.path.join(parent_path, repo)): # Check if dir
            ## Check if git repo (shud have .git folder)
            if ".git" in os.listdir(os.path.join(parent_path, repo)): repo_list.append(os.path.join(parent_path, repo))
            ## Else recurse inside the folder to check for git repos inside it
            else: repo_list.extend(Repo_GetLocalRepos(os.path.join(parent_path, repo)))
    return repo_list

### Imports Parsers ######################################################################################################
def ParseImports_Python_Regex(code_path):
    '''
    Parse Imports - Parses all imports in a python file using Regex
    '''
    # If file does not exist, return empty list
    if not os.path.exists(code_path): return []
    # Init
    code_dir = os.path.dirname(code_path).replace("\\", "/")
    code = open(code_path, "r", encoding="utf8").read()
    code_lines = code.split("\n")
    
    # Parse Imports
    IMPORTS = []
    ignore_state = {
        "active": False,
        "type": "",
        "data": None
    }
    for line in code_lines:
        line = line.strip()
        # Check for ignore statements
        if not ignore_state["active"]:
            ## Check for multi line comments
            if line.startswith('"""'): ignore_state["data"] = '"""'
            elif line.startswith("'''"): ignore_state["data"] = "'''"
            ignore_state["active"] = (ignore_state["data"] is not None)
            if ignore_state["active"]: ignore_state["type"] = "comment_multi"
        if ignore_state["active"] and ignore_state["type"] == "comment_multi":
            if line.endswith(ignore_state["data"]):
                ignore_state = {
                    "active": False,
                    "type": "",
                    "data": None
                }
            continue
        # Check for single line comments
        if line.startswith("#"): continue

        # Init
        KEYWORDS = {
            "import": "import ",
            "as": " as ",
            "from": "from ",
            "from_import": " import "
        }
        # Check for imports
        # CASE 1: import {module1},{module2},...,{modulen}
        if line.startswith(KEYWORDS["import"]):
            ## Get all modules imported in the line
            imports_code = line[len(KEYWORDS["import"]):].strip() # Remove import keyword
            line_imports = imports_code.split(",") # Split into list of modules
            ## Clean for as keyword and form import data
            line_imports_cleaned = []
            for imp in line_imports:
                as_index = imp.find(KEYWORDS["as"]) # Check for as keyword
                if as_index != -1: imp = imp[:as_index] # Remove string after as key word
                imp = imp.strip()
                importData = {
                    "paren_dir": code_dir,
                    "sub_dir": "",
                    "name": imp
                }
                line_imports_cleaned.append(importData)
            IMPORTS.extend(line_imports_cleaned)

        # CASE 2: from {dir1.dir2.dirn} import {module}
        elif line.startswith(KEYWORDS["from"]):
            ## Get directory and module imported in the line
            imports_dirs_code = line[len(KEYWORDS["from"]):].strip() # Remove from keyword
            dir_imports_list = imports_dirs_code.split(KEYWORDS["from_import"]) # Split into list of modules imported from a directory
            import_dir = dir_imports_list[0].strip().replace(".", "/") # Get directory as path
            ## Clean for * keyword and form import data
            line_imports_cleaned = []
            imports_code = dir_imports_list[1].strip()
            ## Check if relative import
            parent_dir, import_dir = Module_CleanModuleDirs(code_dir, import_dir)
            ## Check if importing all functions in a module (* keyword)
            if imports_code == "*":
                module_splitup = import_dir.split("/")
                module_name = module_splitup[-1]
                import_dir = "/".join(module_splitup[:-1])
                import_data = {
                    "parent_dir": parent_dir,
                    "sub_dir": import_dir,
                    "name": module_name
                }
                line_imports_cleaned.append(import_data)
            ## Check if importing functions inside a module - if so only import the main module
            else:
                import_dir = import_dir.rstrip("/")
                import_name, import_package = Pip_SplitModule(import_dir.replace("/", "."))
                ### If final name in heirarchy is a pip module
                if import_name is not None:
                    import_data = {
                        "parent_dir": code_dir,
                        "sub_dir": import_package.replace(".", "/"),
                        "name": import_name
                    }
                    line_imports_cleaned.append(import_data)
                ### Else if final name in heirarchy is a local module
                elif os.path.exists(os.path.join(code_dir, import_dir + ".py")):
                    import_split = os.path.split(import_dir)
                    import_data = {
                        "parent_dir": code_dir,
                        "sub_dir": "/".join(import_split[:-1]),
                        "name": import_split[-1]
                    }
                    line_imports_cleaned.append(import_data)
                ### Else
                else:
                    line_imports = imports_code.split(",") # Split into list of modules
                    for imp in line_imports:
                        as_index = imp.find(KEYWORDS["as"]) # Check for as keyword
                        if as_index != -1: imp = imp[:as_index] # Remove string after as key word
                        imp = imp.strip()
                        importData = {
                            "parent_dir": code_dir,
                            "sub_dir": import_dir,
                            "name": imp
                        }
                        line_imports_cleaned.append(importData)
            IMPORTS.extend(line_imports_cleaned)

    return IMPORTS

def ParseImports_Python(code_path):
    '''
    Parse Imports - Parses all imports in a python file using ast module
    '''
    # If file does not exist, return empty list
    if not os.path.exists(code_path): return []
    # Init
    code_dir = os.path.dirname(code_path).replace("\\", "/")
    code = open(code_path, "r", encoding="utf8").read()
    # Parse Code using AST
    CodeModule = ast.parse(code)
    # functions = [x for x in CodeModule.body if isinstance(x, ast.FunctionDef)]

    # Parse Imports
    IMPORTS = []
    ## Imports
    Imports = [x for x in CodeModule.body if isinstance(x, ast.Import)]
    for imp_g in Imports:
        imps_dicts = []
        for imp in imp_g.names:
            ## Get Module Heirarchy
            name = imp.name.split(".")[-1]
            module = imp.name.rstrip(name).rstrip(".")
            ## Check if relative import
            parent_dir, sub_dir = Module_CleanModuleDirs(code_dir, module.replace(".", "/"))
            ## Form Import Data
            imp_data = {
                "parent_dir": parent_dir,
                "sub_dir": sub_dir,
                "name": name
            }
            imps_dicts.append(imp_data)
        IMPORTS.extend(imps_dicts)
    ## From Imports
    FromImports = [x for x in CodeModule.body if isinstance(x, ast.ImportFrom)]
    for imp_g in FromImports:
        imps_dicts = []
        for imp in imp_g.names:
            ## Get Module Heirarchy
            name = imp.name.split(".")[-1]
            module = imp.name.rstrip(name).rstrip(".")
            if imp_g.module is not None: module = ".".join([module, imp.name.rstrip(name).rstrip(".")]).rstrip(".")
            ## Check if relative import
            parent_dir, sub_dir = Module_CleanModuleDirs(code_dir, module.replace(".", "/"))
            ## Form Import Data
            imp_data = {
                "parent_dir": parent_dir,
                "sub_dir": sub_dir,
                "name": name
            }
            imps_dicts.append(imp_data)
        IMPORTS.extend(imps_dicts)
        
    return IMPORTS

##########################################################################################################################

### BASIC DEPENDENCY TREE ################################################################################################
def DependencyTree_Basic_Python(code_path, level=0, display=False):
    '''
    Dependency Tree - Basic Dependency Tree (Only imports)
    '''
    # Init
    pad_text = "----" * level
    code_dir = os.path.dirname(code_path)
    module_name = os.path.splitext(os.path.basename(code_path))[0]
    module_type = "local" # local file
    if display: print(pad_text + "Module: " + module_name)

    # Parse Imports
    IMPORTS = ParseImports_Python(code_path)
    # Check module types
    ModuleDependencyTree = []
    i, imp_count = 0, len(IMPORTS)
    for imp in IMPORTS:
        sub_module_path = Module_GetPath(imp)
        ## Check if submodule is inbuilt (through pip install) or local => If file exists == local else inbuilt
        sub_module_type = "local" if os.path.exists(sub_module_path) else ("inbuilt" if Pip_CheckModule(imp["name"], imp["sub_dir"].replace("/", ".")) else "missing")
        ## Update
        i += 1
        if display: print(pad_text + "[" + str(i) + " / " + str(imp_count) + "]" + "|" + sub_module_type + "|: " + imp["name"])
        ## Recurse for local modules and set empty parent for inbuilt modules
        sub_module_dependency_tree = []
        if sub_module_type == "local":
            sub_module_dependency_tree = DependencyTree_Basic_Python(sub_module_path, level=level+1, display=display)["dependencies"]
        elif sub_module_type == "inbuilt":
            imp["parent_dir"] = "" # No Parent Dir for inbuilt modules

        sub_module = {
            "name": imp["name"],
            "type": sub_module_type,
            "parent_dir": imp["parent_dir"],
            "sub_dir": imp["sub_dir"],
            "dependencies": sub_module_dependency_tree
        }
        ModuleDependencyTree.append(sub_module)

    Module = {
        "name": module_name,
        "type": module_type,
        "parent_dir": code_dir,
        "sub_dir": "",
        "dependencies": ModuleDependencyTree
    }
    return Module

def DependencyTree_Compress(MODULE, level=0, display=False):
    '''
    Dependency Tree - Compress Dependency Tree (Only imports)
    '''
    # Init
    pad_text = "----" * level
    if display: print(pad_text + "Module: " + MODULE["name"])
    ModuleDependencyTree = MODULE["dependencies"]
    unique_dependencies = {}
    # Loop through all dependencies
    dependency_keys = []
    i, depCount = 0, len(ModuleDependencyTree)
    for dep in ModuleDependencyTree:
        ## Update
        i += 1
        if display: print(pad_text + "[" + str(i) + " / " + str(depCount) + "]" + "|" + dep["type"] + "|: " + dep["name"])
        ## Recurse
        sub_module_Path = Module_GetPath(dep)
        if sub_module_Path not in unique_dependencies.keys():
            dep_cleaned = DependencyTree_Compress(dep, level=level+1, display=display)
            unique_dependencies[sub_module_Path] = Dep_Compress(dep_cleaned)
            unique_dependencies = Dep_UpdateDeps(unique_dependencies, dep_cleaned["dependency_modules"])
        dependency_keys.append(sub_module_Path)
    # Form Compressed Module
    Module_Compressed = {
        "name": MODULE["name"],
        "type": MODULE["type"],
        "parent_dir": MODULE["parent_dir"],
        "sub_dir": MODULE["sub_dir"],
        "dependencies": dependency_keys,
        "dependency_modules": unique_dependencies
    }
    
    return Module_Compressed
##########################################################################################################################

### COMPRESSED DEPENDENCY TREE ###########################################################################################
def DependencyTree_Compressed_Python(code_path, level=0, display=False):
    '''
    Dependency Tree - Generate Compressed Dependency Tree (Only imports) (Direct)
    '''
    # Init
    pad_text = "----" * level
    code_dir = os.path.dirname(code_path)
    module_name = os.path.splitext(os.path.basename(code_path))[0]
    module_type = "local" # local file
    if display: print(pad_text + "Module: " + module_name)
    # Parse Imports
    IMPORTS = ParseImports_Python(code_path)
    # Check module types
    unique_dependencies = {}
    dependency_keys = []
    i, imp_count = 0, len(IMPORTS)
    for imp in IMPORTS:
        sub_module_path = Module_GetPath(imp)
        ## Check if submodule is inbuilt (through pip install) or local => If file exists == local else inbuilt
        sub_module_type = "local" if os.path.exists(sub_module_path) else ("inbuilt" if Pip_CheckModule(imp["name"], imp["sub_dir"].replace("/", ".")) else "missing")
        if sub_module_type == "inbuilt":
            imp["parent_dir"] = ""
            sub_module_path = Module_GetPath(imp)
        ## Update
        i += 1
        if display: print(pad_text + "[" + str(i) + " / " + str(imp_count) + "]" + "|" + sub_module_type + "|: " + imp["name"])
        ## Recurse for local modules and set empty parent for inbuilt modules
        if sub_module_path not in unique_dependencies.keys():
            dep_cleaned = imp
            if sub_module_type == "local":
                dep_cleaned = DependencyTree_Compressed_Python(sub_module_path, level=level+1, display=display)
            else:
                dep_cleaned["type"] = sub_module_type
                if sub_module_type == "inbuilt":
                    dep_cleaned["parent_dir"] = "" # No Parent Dir for inbuilt modules
                dep_cleaned["dependencies"] = [] # No dependencies for inbuilt modules
                dep_cleaned["dependency_modules"] = {}
            dep_cleaned["sub_dir"] = imp["sub_dir"]
            unique_dependencies[sub_module_path] = Dep_Compress(dep_cleaned)
            unique_dependencies = Dep_UpdateDeps(unique_dependencies, dep_cleaned["dependency_modules"])
        dependency_keys.append(sub_module_path)
    # Form Compressed Module
    MODULE = {
        "name": module_name,
        "type": module_type,
        "parent_dir": code_dir,
        "sub_dir": "",
        "dependencies": dependency_keys,
        "dependency_modules": unique_dependencies
    }

    return MODULE
##########################################################################################################################

### REPO LEVEL PYVEN #####################################################################################################
def Repo_FindModules(repo_path, user_name="KausikN", display=False, PROGRESS_OBJ=None):
    '''
    Repo - Find Modules
    '''
    # Init
    repo_path = repo_path.replace("\\", "/")
    repo_name = repo_path.rstrip("/").split("/")[-1]
    # Get all python files in the repo
    CodeFiles = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                CodeFiles.append(os.path.join(root, file))
    # Parse all python files to get imports
    unique_modules = {}
    imported_module_paths = []
    i, f_count = 0, len(CodeFiles)
    for f in CodeFiles:
        ## Update
        i += 1
        if display: print("[" + str(i) + " / " + str(f_count) + "]" + ": " + f)
        ## Parse Imports
        sub_dir = os.path.split(f)[0][len(repo_path):].replace("\\", "/").strip("/")
        module_name = os.path.splitext(os.path.basename(f))[0]
        module_type = "local" # local as file exists
        IMPORTS = ParseImports_Python(f)
        ImportPaths = []
        for imp in IMPORTS:
            abs_path = Module_GetPath(imp, absolute=True)
            path = Module_GetPath(imp, absolute=False)
            if os.path.exists(abs_path): 
                path = os.path.join(sub_dir, path).replace("\\", "/")
            ImportPaths.append(path)
        ## Sort Dependencies
        ImportPaths = sorted(ImportPaths)
        ## Form Module
        module_link = "https://github.com/" + user_name + "/" + repo_name + "/blob/master/" + sub_dir + "/" + module_name + ".py"
        if sub_dir == "": module_link = "https://github.com/" + user_name + "/" + repo_name + "/blob/master/" + module_name + ".py"
        MODULE = {
            "name": module_name,
            "type": module_type,
            "link": module_link,
            "parent_dir": repo_path,
            "sub_dir": sub_dir,
            "dependencies": ImportPaths,
        }
        unique_modules[Module_GetPath(MODULE, absolute=False)] = MODULE
        imported_module_paths.extend(ImportPaths)

    # Check if all imported modules are local or else mark as inbuilt
    imported_module_paths = list(set(imported_module_paths)) # Remove Duplicates
    i = 0
    for path in tqdm(imported_module_paths):
        ## Check if module is inbuilt
        if path not in unique_modules.keys():
            sub_dir = os.path.split(path)[0].replace("\\", "/").strip("/")
            module_name = os.path.splitext(os.path.basename(path))[0]
            module_type = "inbuilt" if Pip_CheckModule(module_name, sub_dir.replace("/", ".")) else "missing"
            parent_dir = repo_path if module_type == "inbuilt" else ""
            MODULE = {
                "name": module_name,
                "type": module_type,
                "link": "", # No Link for inbuilt modules
                "parent_dir": parent_dir,
                "sub_dir": sub_dir,
                "dependencies": [],
            }
            unique_modules[path] = MODULE
        ## Update
        i += 1
        if PROGRESS_OBJ is not None: PROGRESS_OBJ.progress(i / len(imported_module_paths))
    # Sort unique modules
    unique_modules = dict(sorted(unique_modules.items(), key=lambda x: x[0]))
    # Form Repo
    REPO = {
        "name": repo_name,
        "repo_link": "https://github.com/" + user_name + "/" + repo_name,
        "local_path": repo_path,
        "modules": unique_modules
    }

    return REPO