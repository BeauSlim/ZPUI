import importlib
import os
import logging
logger = logging.getLogger(__name__)

class ListWithMetadata(list):
    ordering_alias = None

class AppManager():
    subdir_menus = {}
    """ Example of subdir_menus:
    {'apps/network_apps': <ui.menu.Menu instance at 0x7698ac10>, 
    ...
    'apps/system_apps': <ui.menu.Menu instance at 0x7698abc0>}
    """
    app_list = {}
    """Example of app_list:
    {'apps/network_apps/wpa_cli': <module 'apps.network_apps.wpa_cli.main' from '/root/WCS/apps/network_apps/wpa_cli/main.py'>, 
    'apps/system_apps/system': <module 'apps.system_apps.system.main' from '/root/WCS/apps/system_apps/system/main.py'>, 
    ...
    'apps/network_apps/network': <module 'apps.network_apps.network.main' from '/root/WCS/apps/network_apps/network/main.py'>}
     """

    def __init__(self, app_directory, menu_class, printer_func, i, o):
        logger.debug("AppManager constructor, app_directory = {0}, menu_class= {1}, printer_func={2}, i={3}, o={4}".format(app_directory, menu_class, printer_func, i, o))
        self.app_directory = app_directory
        self.menu_class = menu_class
        self.printer_func = printer_func
        self.i = i
        self.o = o

    def load_all_apps(self):
        logger.debug("entered load_all_apps")
        base_menu = self.menu_class([], self.i, self.o, "Main app menu", exitable=False) #Main menu for all applications.
        orderings = {}
        self.subdir_menus[self.app_directory] = base_menu
        for path, subdirs, modules in app_walk(self.app_directory): 
            logger.debug("Loading path {} with modules {} and subdirs {}".format(path, modules, subdirs))
            for subdir in subdirs:
                #First, we create subdir menus (not yet linking because they're not created in correct order) and put them in subdir_menus.
                subdir_path = os.path.join(path, subdir)
                self.subdir_menus[subdir_path] = self.menu_class([], self.i, self.o, subdir_path)
            for module in modules:
                #Then, we load modules and store them along with their paths
                try:
                    module_path = os.path.join(path, module)
                    app = self.load_app(module_path)
                    logger.debug("Loaded app {}".format(module_path))
                    self.app_list[module_path] = app
                except Exception as e:
                    logger.error("Failed to load app {}".format(module_path))
                    logger.error(e)
                    self.printer_func(["Failed to load", os.path.split(module_path)[1]], self.i, self.o, 2)
        for subdir_path in self.subdir_menus:
            #Now it's time to link menus to parent menus
            if subdir_path == self.app_directory:
                continue
            parent_path = os.path.split(subdir_path)[0]
            ordering = self.get_ordering(parent_path)
            logger.debug("Adding subdir {} to parent {}".format(subdir_path, parent_path))
            parent_menu = self.subdir_menus[parent_path]
            subdir_menu = self.subdir_menus[subdir_path]
            subdir_menu_name = self.get_subdir_menu_name(subdir_path)
            #Inserting by the ordering given
            parent_menu_contents = self.insert_by_ordering([subdir_menu_name, subdir_menu.activate], os.path.split(subdir_path)[1], parent_menu.contents, ordering)
            parent_menu.set_contents(parent_menu_contents)
        for app_path in self.app_list:
            #Last thing is adding applications to menus.
            app = self.app_list[app_path]
            subdir_path = os.path.split(app_path)[0]
            ordering = self.get_ordering(subdir_path)
            logger.debug("Adding app {0} to subdir {1} with callback {2}".format(app_path, subdir_path, app.callback))
            subdir_menu = self.subdir_menus[subdir_path]
            subdir_menu_contents = self.insert_by_ordering([app.menu_name, app.callback], os.path.split(app_path)[1], subdir_menu.contents, ordering)
            subdir_menu.set_contents(subdir_menu_contents)
        #logger.debug("app_list = {0}".format(app_list))
        #logger.debug("subdir_menus = {0}".format(subdir_menus))
        return base_menu

    def load_app(self, app_path):
        logger.debug("entered load_app with app_path = {0}".format(app_path))
        app_import_path = app_path.replace('/', '.')
        logger.debug("app_import_path = {0}".format(app_import_path))
        app = importlib.import_module(app_import_path+'.main', package='apps')
        app.init_app(self.i, self.o)
        return app

    def get_subdir_menu_name(self, subdir_path):
        """This function gets a subdirectory path and imports __init__.py from it. It then gets _menu_name attribute from __init__.py and returns it. 
        If failed to either import __init__.py or get the _menu_name attribute, it returns the subdirectory name."""
        subdir_import_path = subdir_path.replace('/', '.')
        try:
            subdir_object = importlib.import_module(subdir_import_path+'.__init__')
            return subdir_object._menu_name
        except Exception as e:
            print("Exception while loading __init__.py for subdir {}".format(subdir_path))
            print(e)
            return os.path.split(subdir_path)[1]

    def get_ordering(self, path, cache={}):
        """This function gets a subdirectory path and imports __init__.py from it. It then gets _ordering attribute from __init__.py and returns it. It also caches the attribute for faster initialization.
        If failed to either import __init__.py or get the _ordering attribute, it returns an empty list."""
        if path in cache:
            return cache[path]
        import_path = path.replace('/', '.')
        try:
            imported_module = importlib.import_module(import_path+'.__init__')
            ordering = imported_module._ordering
        except ImportError as e:
            print("Exception while loading __init__.py for directory {}".format(path))
            print(e)
            ordering = []
        except AttributeError as e:
            #print("No ordering for directory {}".format(path))
            #print(e)
            ordering = []
        finally:
            cache[path] = ordering
            return ordering

    def insert_by_ordering(self, to_insert, alias, l, ordering):
        #print("Inserting {} by ordering {}".format(alias, ordering))
        if alias in ordering:
            #HAAAAAAAAAAAAAAXXXXXXXXXX
            to_insert = ListWithMetadata(to_insert)
            #Marking the object we're inserting with its alias 
            #so that we won't mix up ordering of elements later
            to_insert.ordering_alias = alias 
            if not l: #No conditions to check
                l.append(to_insert); return l
            for e in l:
                #print("{} - {}".format(type(e), e))
                if hasattr(e, "ordering_alias"):
                    if ordering.index(e.ordering_alias) > ordering.index(alias):
                        l.insert(l.index(e), to_insert); return l
                    else:
                        pass #going to next element
                else:
                    l.insert(l.index(e), to_insert); return l
        l.append(to_insert); return l #Catch-all

def app_walk(base_dir):
    """Example of app_walk(directory):  
    [('./apps', ['ee_apps', 'media_apps', 'test', 'system_apps', 'skeleton', 'network_apps'], ['__init__.pyc', '__init__.py']),
    ('./apps/ee_apps', ['i2ctools'], ['__init__.pyc', '__init__.py']),
    ('./apps/ee_apps/i2ctools', [], ['__init__.pyc', '__init__.py', 'main.pyc', 'main.py']),
    ('./apps/media_apps', ['mocp', 'volume'], ['__init__.pyc', '__init__.py']),
    ('./apps/media_apps/mocp', [], ['__init__.pyc', '__init__.py', 'main.pyc', 'main.py']),
    ('./apps/media_apps/volume', [], ['__init__.pyc', '__init__.py', 'main.pyc', 'main.py'])]
    """
    walk_results = []
    modules = []
    subdirs = []
    for element in os.listdir(base_dir):
        full_path = os.path.join(base_dir,element)
        if os.path.isdir(full_path):
            if is_subdir(full_path):
                subdirs.append(element)
                results = app_walk(full_path)
                for result in results:
                    walk_results.append(result)
            elif is_module_dir(full_path):
                modules.append(element)
    walk_results.append((base_dir, subdirs, modules))
    return walk_results

def is_module_dir(dir_path):
    contents = os.listdir(dir_path)
    if "main.py" in contents:
        if 'do_not_load' not in contents:
            return True
    return False

def is_subdir(dir_path):
    contents = os.listdir(dir_path)
    if "__init__.py" in contents and "main.py" not in contents and "do_not_load" not in contents:
        return True
    else:
        return False

