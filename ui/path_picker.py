import os

from menu import Menu, MenuExitException, to_be_foreground
from printer import Printer
from helpers import setup_logger
logger = setup_logger(__name__, "warning")

class PathPicker(Menu):

    path_chosen = None

    def __init__(self, path, i, o, callback = None, name = None, display_hidden = False, dirs_only = False, current_dot = False, prev_dot = True, scrolling=True, **kwargs):
        """Initialises the PathPicker object.

        Args:

            * ``path``: a path to start from.
            * ``i``, ``o``: input&output device objects.

        Kwargs:

            * ``callback``: if set, PathPicker will call the callback with path as first argument upon selecting path, instead of exiting the activate().
            * ``dirs_only``: if True, PathPicker will only show directories.
            * ``current_dot``: if True, PathPicker will show '.' path.
            * ``prev_dot``: if True, PathPicker will show '..' path.
            * ``display_hidden``: if True, PathPicker will display hidden files.

        """
        Menu.__init__(self, [], i, o, entry_height=1, scrolling=True, append_exit=False, catch_exit=False, contents_hook=None, **kwargs)
        if not os.path.isdir(path):
             raise ValueError("PathPicker path has to be a directory!")
        self.base_name = name if name else "PathPicker"
        self.display_hidden = display_hidden
        self.callback = callback
        self.dirs_only = dirs_only
        self.current_dot = current_dot
        self.prev_dot = prev_dot
        self.menu_pointers = {}
        self.set_path(os.path.normpath(path))
        self.update_keymap()

    def before_activate(self):
        #Clearing flags
        Menu.before_activate(self)
        path_chosen = None

    def get_return_value(self):
        return self.path_chosen

    @to_be_foreground
    def select_entry(self):
        """
        |Is typically used as a callback from input event processing thread.
        |After callback's execution is finished, sets the keymap again and refreshes the screen.
        |If menu has no elements, exits the menu.
        |If MenuExitException is returned from the callback, exits menu, too."""
        logger.debug("element selected")
        if len(self.contents) > 0:
            self.to_background()
            self.contents[self.pointer][1]()
            self.to_foreground()
            if self.path_chosen:
                self.deactivate()
            else:
                self.to_foreground()

    def update_keymap(self):
        """Updates the keymap."""
        self.keymap.update({
            "KEY_RIGHT":lambda: self.options_menu(),
            "KEY_LEFT": lambda: self.go_back()
        })

    def go_back(self):
        if self.path == '/':
            self.deactivate()
            return
        parent_path = os.path.split(self.path)[0]
        self.goto_dir(parent_path)

    def set_path(self, path):
        self.path = path
        self.name = "{}-{}".format(self.base_name, self.path)
        self.set_contents(self.regenerate_contents())

    def regenerate_contents(self):
        print("Regenerating contents")
        contents = []
        self.pointer = 0
        if self.path != '/':
            if self.current_dot or self.prev_dot:
                dot_path = os.path.join(self.path, '.')
                if self.current_dot: contents.append(['.', lambda: self.goto_dir(dot_path)])
                if self.prev_dot: contents.append(['..', lambda: self.goto_dir(dot_path+'.')])
        path_contents = os.listdir(self.path)
        files = []
        dirs = []
        for item in path_contents:
            full_path = os.path.join(self.path, item)
            if os.path.isdir(full_path):
                if not (self.display_hidden and item.startswith('.')):
                    dirs.append(item)
            else:
                if not (self.display_hidden and item.startswith('.')):
                    if not self.dirs_only:
                        files.append(item)
        dirs.sort()
        files.sort()
        for dir in dirs:
            full_path = os.path.join(self.path, dir)
            if self.dirs_only:
                isdir = lambda x: os.path.isdir(os.path.join(full_path, x))
                dirs_in_dir = [isdir(e) for e in os.listdir(full_path)]
                if any(dirs_in_dir):
                    #Directory has other directories inside
                    contents.append([dir, lambda x=full_path: self.goto_dir(x), lambda: True])
                else:
                    #Directory has no other directories inside
                    contents.append([dir, lambda x=full_path: self.select_path(x)])
            else:
                contents.append([dir, lambda x=full_path: self.goto_dir(x), lambda: True])
        for file in files:
            full_path = os.path.join(self.path, file)
            contents.append([file, lambda x=full_path: self.select_path(x)])
        return contents

    @to_be_foreground
    def options_menu(self):
        self.to_background()
        current_item = self.contents[self.pointer][0]
        full_path = os.path.join(self.path, current_item)
        def get_contents():
            dh_option_label = "Hide .-files" if self.display_hidden else "Show .-files"
            contents = [["Select path",lambda x=full_path: self.option_select(x)],
                        [dh_option_label, self.toggle_display_hidden],
                        ["See full name",lambda x=full_path: Printer(current_item, self.i, self.o)],
                        ["See full path",lambda x=full_path: Printer(x, self.i, self.o)],
                        ["Exit PathPicker", self.option_exit]]
            return contents
        Menu([], self.i, self.o, contents_hook=get_contents, name="PathPicker context menu").activate()
        if self.in_background:
            self.set_contents(self.regenerate_contents())
            self.to_foreground()

    def toggle_display_hidden(self):
        self.display_hidden = not self.display_hidden

    def option_exit(self):
        self.deactivate()
        raise MenuExitException #Menu needs to exit when PathPicker exits. It doesn't, of course, as it's in the main loop, so the app's left hanging.
        #One of the reasons MenuExitExceptions are there.

    def option_select(self, path):
        path = os.path.normpath(path)
        if self.callback is None:
            self.select_path(path)
            self.deactivate()
            raise MenuExitException
        else:
            self.callback(path)
            raise MenuExitException

    #@to_be_foreground
    def goto_dir(self, dir):
        dir = os.path.normpath(dir)
        self.menu_pointers[self.path] = self.pointer
        self.set_path(dir)
        if self.path in self.menu_pointers:
            pointer = self.menu_pointers[self.path]
            #If parent directory changed contents while we were browsing child directory, the count will be different
            #So, a quick check
            if pointer >= len(self.contents):
                self.pointer = len(self.contents)-1
            else:
                self.pointer = pointer
        else:
            self.pointer = 0
        self.view.refresh()

    #@to_be_foreground
    def select_path(self, path):
        path = os.path.normpath(path)
        if self.callback is not None:
            self.to_background()
            current_item = self.contents[self.pointer][0]
            full_path = os.path.join(self.path, current_item)
            self.callback(full_path)
            self.to_foreground()
        else:
            self.path_chosen = path
