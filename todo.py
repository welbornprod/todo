#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" todo.py
    ...A revamp of my quick and dirty todo list app.
    -Christopher Welborn 07-21-2014
"""

import functools
import json
import os
import re
import sys
from collections import UserDict, UserList

import docopt

NAME = 'Todo'
VERSION = '2.1.0'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}
    Usage:
        {script} [-c | -h | -j | -v] [-D]
        {script} [-a | -b | -d | -i | -r | -R | -s | -t | -u] KEY ITEM [-D]
        {script} [-a | -b | -d | -i | -r | -R | -s | -t | -u] ITEM [-D]
        {script} -a [-i] KEY ITEM [-D]
        {script} -a [-i] ITEM [-D]
        {script} -e FILE KEY [-D]
        {script} -I KEY ITEM [-D]
        {script} -I ITEM [-D]
        {script} -K KEY [-D]
        {script} -l [KEY] [-D]
        {script} -L [-D]
        {script} -m KEY ITEM <new_key> [-D]
        {script} -m ITEM <new_key> [-D]
        {script} -n [KEY] <new_keyname> [-D]
        {script} -p KEY ITEM <new_position> [-D]
        {script} -p ITEM <new_position> [-D]

    Options:
        KEY                    : Key or label for the item.
                                 Defaults to 'No Label'.
        ITEM                   : Item to add, or query to use when finding
                                 an item. When looking items up, the item
                                 number may also be used.
        <new_key>              : New key for item when moving between keys.
        <new_keyname>          : New key name when renaming a key.
        <new_position>         : New position number for item when position
                                 action is used.
                                 Index must be (>= 0 and < list length).
                                 You may also use 't[op]', or 'b[ottom]'.
        -a,--add               : Add an item to the list.
                                 You may omit this option and just enter
                                 the item (with optional key first),
                                 unless you want to mark an item as
                                 important while adding it.
        -b,--bottom            : Unprioritize item. (put on the bottom).
        -c,--clear             : Clear all items. Confirmation needed.
        -d,--down              : Bump item down one spot on the list.
        -D,--debug             : Debug mode, prints extra information.
                                 Gives you a look into what's going on
                                 behind the scenes.
        -e FILE,--export FILE  : Export a key's items as JSON.
                                 FILE should be the file name for an existing
                                 JSON file, or a non-existant file.
                                 If '-' is passed, content will be printed to
                                 stdout.
        -h,--help              : Show this help message.
        -i,--important         : Mark item as important (bold/red).
        -I,--unimportant       : Mark item as unimportant.
        -j,--json              : Show list in JSON format.
        -K,--removekey         : Remove a key/label. (includes all items)
        -l,--list              : List items from a certain key.
                                 Defaults to: (first key)
        -L,--listall           : List all items from all keys.
                                 This is the default action when no
                                 arguments are given.
        -m,--movetokey         : Move item to new or other key.
        -n,--renamekey         : Give a key another name/label.
        -p,--position          : Move item to a new position in the same
                                 key.
        -r,--remove            : Remove an item from the list.
                                 Accepts item number or regex to match.
                                 Confirmation is needed.
        -R,--REMOVE            : Same as --remove, no confirmation though.
        -s,--search            : Search for items by index or regex/text.
        -t,--top               : Prioritize item (put on top of the list).
        -u,--up                : Bump item up one spot on the list.
        -v,--version           : Show version.
""".format(script=SCRIPT, versionstr=VERSIONSTR)

# Global flags/settings. ------------------------------------------
DEBUG = False
DEBUGARGS = False
DEFAULTFILE = os.path.join(SCRIPTDIR, 'todo.lst')
LOCALFILE = os.path.join(os.getcwd(), 'todo.lst')
# Global TodoList() to work with (..set in main())
todolist = None


# Main entry point ------------------------------------------------


def main(argd):
    """ Main entry point, expects doctopt arg dict as argd """
    global DEBUG, todolist, userkey, useritem
    DEBUG = argd['--debug']
    if DEBUGARGS:
        DEBUG = True
        printdebug("Arguments:", data=argd)
        return 0

    # Look for a local copy of todo.lst before loading the global list.
    todofile = LOCALFILE if os.path.exists(LOCALFILE) else DEFAULTFILE

    # Load todolist if available.
    try:
        todolist = TodoList(filename=todofile)
    except TodoList.NoFileExists:
        printdebug('No file exists at: {}'.format(todofile))
    except TodoList.ParseError as exparse:
        printstatus('The todo.lst couldn\'t be loaded!', error=exparse)
        return 1
    except Exception as ex:
        printstatus('There was an error while loading the list:', error=ex)
        return 1

    if todolist is None:
        todolist = TodoList()
        todolist.filename = todofile
    printheader(todolist)

    # Build a map of cmdline-args to functions.
    # Return the proper function to run, or None.
    runaction = get_action(argd)
    if runaction is None:
        # Default actions when no args are present.
        if argd['ITEM']:
            # If the item is actually the name of a key, list that key.
            trykey = todolist.get_key(argd['ITEM'])
            if trykey:
                return do_listkey(trykey)

            # User is adding an item.
            kwargs = {
                'key': (argd['KEY'] or TodoKey.null),
                'important': argd['--important'],
            }
            return do_add(argd['ITEM'], **kwargs)

        # User is listing all items.
        return do_listall()

    # Run the action that was chosen based on cmdline-args.
    retvalue = runaction()

    printdebug(text='Todo Items after this run:', data=todolist)
    return retvalue

# Functions -------------------------------------------------------


def build_actions(argdict):
    """ Builds a dict of command-line args mapped to their function,
        arguments are prefilled.
    """
    useritem = argdict['ITEM'] or None
    rawkey = argdict['KEY']
    userkey = rawkey or TodoKey.null
    printdebug('Using key: {}'.format(userkey))

    userimportant = argdict['--important']
    actions = {
        '--add': {
            'function': do_add,
            'args': [useritem],
            'kwargs': {'key': userkey, 'important': userimportant},
        },
        '--bottom': {
            'function': do_move_item,
            'args': [useritem, 'bottom'],
            'kwargs': {'key': userkey},
        },
        '--clear': {
            'function': do_clear,
        },
        '--down': {
            'function': do_move_item,
            'args': [useritem, 'down'],
            'kwargs': {'key': userkey},
        },
        '--export': {
            'function': do_export,
            'kwargs':  {'key': userkey, 'filename': argdict['--export']}
        },
        '--important': {
            'function': do_mark_important,
            'args': [useritem],
            'kwargs': {
                'key': userkey,
                'adding': argdict['--add'],
                'important': True
            },
        },
        '--json': {
            'function': do_json,
        },
        '--list': {
            'function': do_listkey,
            'kwargs': {'key': userkey},
        },
        '--listall': {
            'function': do_listall,
        },
        '--movetokey': {
            'function': do_move_tokey,
            'args': [useritem],
            'kwargs': {'key': userkey, 'newkey': argdict['<new_key>']},
        },
        '--position': {
            'function': do_move_item,
            'args': [useritem, argdict['<new_position>']],
            'kwargs': {'key': userkey},
        },
        '--remove': {
            'function': do_remove,
            'args': [useritem],
            'kwargs': {'key': userkey, 'confirmation': True},
        },
        '--REMOVE': {
            'function': do_remove,
            'args': [useritem],
            'kwargs': {'key': userkey, 'confirmation': False},
        },
        '--removekey': {
            'function': do_removekey,
            'kwargs': {'key': userkey},
        },
        '--renamekey': {
            'function': do_renamekey,
            'args': [argdict['<new_keyname>']],
            'kwargs': {'key': userkey},
        },
        '--search': {
            'function': do_search,
            'args': [useritem],
            'kwargs': {'key': rawkey},
        },
        '--top': {
            'function': do_move_item,
            'args': [useritem, 'top'],
            'kwargs': {'key': userkey},
        },
        '--unimportant': {
            'function': do_mark_important,
            'args': [useritem],
            'kwargs': {'key': userkey, 'important': False},
        },
        '--up': {
            'function': do_move_item,
            'args': [useritem, 'up'],
            'kwargs': {'key': userkey},
        },
    }
    return actions


def check_empty_key(key=None):
    """ Check to see if a key is empty, and offer to remove it if it is. """
    todokey = todolist.get_key(key)
    if todokey is None:
        printdebug('Invalid empty key check for: {} (is {})'.format(
            key,
            todokey))
        return False

    if len(todokey) == 0:
        printdebug('Key is empty: {}'.format(todokey.label))
        warn = ('This key is empty now:', todokey.label)
        msg = 'Would you like to remove the key?'
        if confirm(msg, warn=warn):
            printdebug('Removing empty key: {}'.format(todokey.label))
            return True if do_removekey(key) == 0 else False

    printdebug('Key was not empty.')
    return False


def confirm(question, header=None, warn=None, forceanswer=False):
    """ Confirm a yes/no question, returns True/False (yes/no).
        Optional header and/or warning msg printed before the question.
    """

    if header:
        print('\n{}'.format(header))
    if warn:
        if isinstance(warn, str):
            print('\n{}'.format(colorerr(warn)))
        elif isinstance(warn, (list, tuple)):
            print('\n{} {}'.format(colorerr(warn[0]), colorval(warn[1])))

    if not question.endswith('?'):
        question = '{}?'.format(question)
    if not question.startswith('\n'):
        question = '\n{}'.format(question)
    question = '{} (y/N): '.format(question)

    ans = input(question).lower()
    while forceanswer and (not ans):
        ans = input(question).lower()

    return (ans[0] == 'y') if ans else False


def do_add(text, key=None, important=False):
    """ Add an item to the todo list. (Key is optional.) """
    if not text:
        printstatus('No item to add!', error=True)
        return 1
    printdebug('do_add(key={},important={},"{}")'.format(key, important, text))
    key, newitem = todolist.add_item(text, key=key, important=important)
    printstatus('Added item:', key=key, item=newitem)
    return do_save()


def do_clear():
    """ Clear all items (after confirmation.) """
    itemcnt = todolist.get_count()
    confirmwarn = 'This will clear all {} items from the list.'.format(itemcnt)
    confirmmsg = 'Clear the entire todo list?'
    if confirm(confirmmsg, warn=confirmwarn):
        todolist.clear()
        return do_save()

    printstatus('User cancelled.', error=True)
    return 1


def do_export(key=None, filename=None):
    """ Export a key, or all keys to another JSON file.

        Arguments:
            key       : TodoKey to export.
            filename  : Existing or new JSON file name. Content will be printed
                        to stdout if '-' is given.
    """
    todokey = get_key(key or TodoKey.null)
    if todokey is None:
        return 1

    if filename == '-':
        print(todokey.to_json())
        return 0

    printstatus('Merging key into {}:'.format(filename), key=todokey)
    return 0 if merge_json(todokey.to_json_obj(), filename) else 1


def do_json():
    """ Print JSON format of TodoList. """
    try:
        jsondata = todolist.to_json()
    except TodoList.ParseError:
        printstatus('Unable to format JSON!', error=True)
        return 1

    print(jsondata)
    return 1


def do_listall():
    """ List all items in all keys. """
    retall = 0
    names = todolist.keynames()
    for keyname in names:
        ret = do_listkey(keyname)
        if ret == 1:
            retall = 1
            printstatus('Error listing key:', key=keyname, error=True)
    if not names:
        msg = color('No items saved yet.', fore='red')
        print('\n{}\n'.format(msg))
    return retall


def do_listkey(key=None):
    """ List all items within a key. """
    todokey = get_key(key or TodoKey.null)

    if todokey is None:
        return 1

    if todokey:
        print('    {}'.format(str(todokey).replace('\n', '\n    ')))
    else:
        print('    {}'.format(str(todokey)))
        printstatus('        (no items in this key)', error=True, nobreak=True)
    return 0


def do_mark_important(query, key=None, adding=False, important=True):
    """ Mark an existing item as important. The 'adding' flag short-circuits
        this function and does 'do_add' instead. It is because of the way
        arguments are handled (the way functions are fired off.)
    """
    if adding:
        return do_add(query, key=key, important=important)

    todokey = get_key(key or TodoKey.null)
    if todokey is None:
        return 1

    index, item = todokey.find_item(query)
    if (index is None) or (item is None):
        printstatus('Unable to find that item:', item=query, error=True)
        return 1

    item.important = important
    importantstr = 'important' if important else 'unimportant'
    msg = 'Marked as {}:'.format(importantstr)
    printstatus(msg, key=todokey, index=index, item=item)
    return do_save()


def do_move_item(query, newindex, key=None):
    """ Move an item from one position to another inside it's key. """
    if not newindex:
        printstatus('Invalid new position given:', index=newindex, error=True)
        return 1
    key = key or TodoKey.null
    todokey = get_key(key)
    if todokey is None:
        return 1
    maxlength = todokey.get_count() - 1
    # Position modifier shortcuts ('top', 'bottom', 'down', 'up')
    # Holds a function that will convert the current index into the new one.
    position_mod = {
        't': lambda i: 0,
        'b': lambda i: maxlength,
        'u': lambda i: (i - 1) if (i > 0) else 0,
        'd': lambda i: (i + 1) if (i < maxlength) else maxlength,
    }
    # Make sure the item exists, we may need its index anyway.
    foundindex, founditem = todokey.find_item(query)
    if (founditem is None) or (foundindex is None):
        printstatus('Unable to find that item:', item=query)
        return 1

    if newindex.lower()[0] in position_mod:
        # Modify the new index using shortcuts 'top', 'bottom', 'up', 'down'.
        newindex = position_mod[newindex.lower()[0]](foundindex)
    else:
        # Set the index the user wants.
        try:
            newindex = int(newindex)
        except (TypeError, ValueError):
            printstatus('Invalid new position:', index=newindex)

    indexstr = '{} -> {}'.format(foundindex, newindex)
    errmsg = 'Unable to move item:'
    try:
        movediteminfo = todolist.move_item(query, newindex, key=key)
    except TodoList.BadIndexError as exindex:
        printstatus(errmsg, index=indexstr, item=founditem, error=exindex)
        return 1

    tdkey, oindex, nindex, item = movediteminfo
    if nindex is None:
        printstatus(errmsg, key=key, index=indexstr, item=founditem)
        return 1

    # okay.
    printstatus('Moved:', key=key, index=indexstr, item=founditem)
    return do_save()


def do_move_tokey(query, newkey, key=None):
    """ Move an item from one key to another, or to a new key. """
    key = key or TodoKey.null
    oldkey, movedkey, item = todolist.move_item_tokey(query, newkey, key=key)
    keystr = '{} -> {}'.format(key, newkey)
    if (oldkey is None) and (newkey is None) and (item is None):
        printstatus('Unable to do move:', key=keystr, item=query)
        return 1

    printstatus('Move item:', key=keystr, item=item)

    if check_empty_key(oldkey):
        # No save (do_removekey already saved).
        return 0
    return do_save()


def do_remove(query, key=None, confirmation=True):
    """ Remove an item (if no key is given, the default key is used.) """
    key = key or TodoKey.null
    if confirmation:
        foundkey, index, item = todolist.find_item(query, key=key)
        if (index is not None) and (item is not None):
            warn = (
                'This will remove the item:',
                '{}...'.format(str(item)[:40]))
            msg = 'Are you sure you want to remove this item?'
            if not confirm(msg, warn=warn):
                printstatus('User Cancelled', error=True)
                return 1

    removed = todolist.remove_item(query, key=key)
    if removed is None:
        printstatus('Could not find:', key=key, item=query)
        return 1

    printstatus('Removed:', key=key, item=removed)

    # Offer to delete the key if it is empty.
    if check_empty_key(key):
        # No save (do_removekey already saved),
        return 0

    printdebug('Key still has items: {}'.format(key))
    return do_save()


def do_removekey(key=None, confirmation=True):
    """ Remove a key and all of it's items. """
    key = key or TodoKey.null
    todokey = get_key(key)
    if todokey is None:
        return 1

    itemcnt = len(todokey)
    if itemcnt > 1 and confirmation:
        warnmsg = 'This will delete {} items!'.format(itemcnt)
        msg = 'Are you sure you want to delete {}?'.format(colorkey(key))
        if not confirm(msg, warn=warnmsg):
            printstatus('User cancelled.', error=True)
            return 1

    del todolist.data[key]
    printstatus('Removed:', key=key)
    return do_save()


def do_renamekey(newkeyname, key=None):
    """ Rename a key. """
    key = key or TodoKey.null
    # TODO: All of these checks need to be TodoList methods...
    # TODO: write TODO comments in the TODO apps code.
    # TODO: use the Todo app to write TODOS.

    # Renaming to the same name? But why.
    if key == newkeyname:
        printstatus('Key already has that name:', key=key, error=True)
        return 1
    # Make sure old key exists.
    existingkey = get_key(key)
    if existingkey is None:
        return 1
    # If the new name exists, it would break things. Try 'merging' keys.
    existingnewkey = todolist.get_key(newkeyname, None)
    if existingnewkey is not None:
        printstatus('New key name already taken:', key=newkeyname, error=True)
        return 1

    # Try renaming the key.
    newkey = todolist.rename_key(newkeyname, key=key)
    if newkey is None:
        printstatus('Unable to rename key:', key=key)
        return 1

    keystr = '{} -> {}'.format(key, newkey.label)
    printstatus('Renamed key:', key=keystr)
    return do_save()


def do_save():
    """ Save all items to disk. """
    itemcount = todolist.save_file()
    if itemcount > 0:
        printstatus('Items saved:', index=itemcount)
        return 0
    elif itemcount == 0:
        printstatus('Items saved. (list is blank)')
        return 0
    # Error saving.
    printstatus('Unable to save items!', error=True)
    return 1


def do_search(query, key=None):
    """ Search items within a key, or all items using index or regex pattern.
    """
    if key is None:
        results = todolist.search_items(query)
    else:
        todokey = get_key(key)
        if todokey is None:
            return 1
        results = [(key, todokey.search_items(query))]

    total = 0
    for keyname, iteminfo in results:
        print(colorkey('{}:'.format(keyname)))
        for index, item in iteminfo:
            indexstr = color(str(index), style='bright')
            msg = '    {}: {}'.format(indexstr, item)
            print(msg)
            total += 1

    resultmsg = 'result found.' if total == 1 else 'results found.'
    printstatus('{} {}'.format(str(total), resultmsg))
    return 0 if total else 1


def get_action(argdict):
    """ Return a function to run based on user args. If no action can be found,
        (no args present) then None is returned.
    """
    actions = build_actions(argdict)
    for argname in actions:
        if argdict[argname]:
            # Action arg is present, run the function and end.
            info = actions[argname]
            func = info['function']
            args = info.get('args', [])
            kwargs = info.get('kwargs', {})
            if DEBUG:
                fname = func.__name__
                dbugmsg = (
                    'get_action(): '
                    '{} -> {}'
                    '({}, {})').format(argname, fname, args, kwarg_str(kwargs))
                printdebug(dbugmsg)
            # Return the function with the appropriate arguments/keyword-args.
            return functools.partial(func, *args, **kwargs)
    return None


def get_filenames(fore=None, back=None, style=None):
    """ Return a list of acceptable todo.lst file paths.
        Returns [DEFAULTFILE] or [DEFAULTFILE, LOCALFILE].
        Arguments:
            fore, back, style : Arguments for color().
                                If any of these arguments are given,
                                color() is called on each item before returning
                                the list.

    """
    if DEFAULTFILE == LOCALFILE:
        files = [DEFAULTFILE]
    else:
        files = sorted((DEFAULTFILE, LOCALFILE))

    if any((fore, back, style)):
        return [color(s, fore=fore, back=back, style=style) for s in files]
    return files


def get_key(keyname=None):
    """ Wrapper for todolist.get_key(). If an invalid keyname is passed,
        an error message is printed and None is returned.
        With a valid keyname, the actual TodoKey() is returned.
    """
    # A TodoKey may have been passed to another command like do_listkey..
    if isinstance(keyname, TodoKey):
        return keyname

    if keyname is None:
        keyname = TodoKey.null
    key = todolist.get_key(keyname, default=None)
    if key is None:
        printstatus('No key named:', key=keyname, error=True)
        return None
    return key


def kwarg_str(d):
    """ Just converts a dict into a keyword-arg-looking string.
        kwarg_str({'this': True, 'thing': 25}) == 'this=True, thing=25'
        For use in debug messages.
    """
    if hasattr(d, 'items'):
        return ', '.join('{}={}'.format(k, v) for k, v in d.items())
    return ''


def merge_json(dictobj, filename):
    """ Merge JSON data into an existing JSON file, or create a new file.
        Arguments:
            dictobj   : A dict with string keys. These keys will be updated
                        in an existing JSON dict, or created for new files.
                        This dict should already be JSON serializable.
            filename  : New or existing JSON file name.
    """

    # Try reading existing JSON data.
    try:
        with open(filename, 'r') as fread:
            data = fread.read()
        printdebug('Using existing data from: {}'.format(filename))
    except FileNotFoundError:
        printdebug('Creating a new JSON file: {}'.format(filename))
        data = '{}'

    # Create object from existing JSON, even if it's just an empty dict.
    try:
        jsondata = json.loads(data)
    except ValueError as ex:
        printstatus('Not a valid JSON file: {}'.format(filename), error=ex)
        return False

    # Merge new data with the old.
    try:
        jsondata.update(dictobj)
    except (AttributeError, TypeError):
        printstatus('\n'.join((
            'Not a valid JSON dict: {filename}',
            'Trying to merge: {newdata!r}',
            '           into: {olddata!r}')).format(
                filename=filename,
                newdata=dictobj,
                olddata=jsondata))
        return False

    # Write the result to file.
    try:
        with open(filename, 'w') as f:
            json.dump(jsondata, f, indent=4, sort_keys=True)
    except EnvironmentError as exwrite:
        printstatus(
            'Failed to write JSON data: {}'.format(filename),
            error=exwrite)
        return False
    except (ValueError, TypeError) as exjson:
        printstatus(
            'Failed to create JSON: {}'.format(filename),
            error=exjson)
        return False

    return True


def printdebug(text=None, data=None):
    """ Debug printer. Prints simple text, or pretty prints dicts/lists. """
    if DEBUG:
        if text:
            print(colordebug(text))
        if data:
            printobj(data)


def printheader(todolst=None):
    """ Print the program header message. """
    # Use the global todolist when not specified.
    if todolst is None:
        todolst = todolist

    if todolst:
        # When the todo list has items print the header.
        itemcount = todolst.get_count()
        itemcountstr = color(str(itemcount), fore='blue', style='bold')
        itemplural = 'item' if itemcount == 1 else 'items'
        headerstr = ' '.join((
            color('Todo', style='bold'),
            'list loaded from:',
            color(todolst.filename, fore='blue'),
            '({} {})'.format(itemcountstr, itemplural)
        ))
    else:
        if todolst.filename and os.path.exists(todolst.filename):
            # Empty, or new todolist.
            headerstr = ' '.join((
                color('Todo', style='bold'),
                'list loaded from:',
                color(todolst.filename, fore='blue'),
                '({})'.format(color('Empty', fore='blue', style='bold'))
            ))
        else:
            # Uninitialized TodoList.
            filemsg = color('No todo.lst found', fore='blue', style='bold')
            headerstr = ' '.join((
                color('Todo', style='bold'),
                'v.',
                VERSION,
                'loaded.',
                '({})'.format(filemsg)
            ))
            # Add an extra help message about what files we are looking for.
            filenames = get_filenames(fore='cyan')
            defaultfiles = '\n    '.join(filenames)
            if len(filenames) == 1:
                fileplural = 'this file'
            else:
                fileplural = 'one of these files'
            filewarn = '\n'.join((
                'Add an item, or create {}:',
                '    {}'
            )).format(fileplural, defaultfiles)
            headerstr = '\n'.join((headerstr, filewarn))

    print(headerstr)


def printobj(d, indent=0):
    """ Print a dict/list/tuple, with pretty formatting.
        Uses color from ColorCodes (colorkey(), colorval())
    """
    if isinstance(d, TodoKey):
        printobj(d.to_dict(), indent=indent)
    elif isinstance(d, TodoList):
        for keyname in d.data:
            todokey = d.get_key(keyname)
            if todokey is None:
                errmsg = 'printobj(TodoList) failed on: {}'.format(keyname)
                printstatus(errmsg, error=True)
                continue
            print('{}{}:'.format(' ' * indent, colorkey(todokey.label)))
            printobj(todokey, indent=indent + 4)
    elif isinstance(d, dict):
        for k in sorted(d):
            v = d[k]
            print('{}{}:'.format(' ' * indent, colorkey(str(k))))
            if isinstance(v, dict):
                printobj(v, indent=indent + 4)
            elif isinstance(v, (list, tuple)):
                printobj(v, indent=indent + 4)
            else:
                print('{}{}'.format(' ' * (indent + 4), colorval(str(v))))
    elif isinstance(d, (list, tuple)):
        for itm in sorted(d):
            if isinstance(itm, (list, tuple)):
                printobj(itm, indent=indent + 4)
            else:
                print('{}{}'.format(' ' * indent, colorval(str(itm))))
    else:
        print('{}{}'.format(' ' * indent, colorval(str(d))))


def printstatus(
        msg, key=None, index=None, item=None, error=False, nobreak=False):
    """ Prints a color-coded status message.
        If error is Truthy, the message will be red.
        If error is an Exception, the error message will be printed also.
        Arguments:
            msg      : Message to print.
            key      : Optional key name or TodoKey for formatting key names.
            index    : Optional index (int) for formatting indexes.
            item     : Optional str or TodoItem for formatting items.
            error    : Optional Exception, or True for printing error messages.
            nobreak  : Whether to use spaces to separate each piece of info.
    """
    msgfmt = ['{message}']
    if error:
        msgargs = {'fore': 'red'}
    else:
        msgargs = {'fore': 'cyan'}
    msgfmtargs = {'message': color(msg, **msgargs)}
    if key is not None:
        msgfmt.append('[{keyname}]')
        keystr = key.label if isinstance(key, TodoKey) else str(key)
        msgfmtargs['keyname'] = colorkey(keystr)
    if index is not None:
        msgfmt.append('[{index}]')
        msgfmtargs['index'] = color(
            str(index),
            fore='magenta',
            style='bold')
    if item is not None:
        msgfmt.append('{item}')
        msgfmtargs['item'] = color(str(item), fore='green')

    print(''.join((
        '' if nobreak else '\n',
        ' '.join(msgfmt).format(**msgfmtargs)
    )))
    # Print the exception message if it was passed with 'error'.
    if isinstance(error, Exception):
        errmsg = str(error)
        if errmsg:
            print(colorerr(errmsg))

# Classes ---------------------------------------------------------


class ColorCodes(object):

    """ This class colorizes text for an ansi terminal. """

    def __init__(self):
        # Linux style color code numbers.
        self.codes = {
            'fore': {
                'black': '30', 'red': '31',
                'green': '32', 'yellow': '33',
                'blue': '34', 'magenta': '35',
                'cyan': '36', 'white': '37',
                'reset': '39'},
            'back': {
                'black': '40', 'red': '41', 'green': '42',
                'yellow': '43', 'blue': '44',
                'magenta': '45', 'cyan': '46', 'white': '47',
                'reset': '49'},
            'style': {
                'bold': '1', 'bright': '1', 'dim': '2',
                'normal': '22', 'none': '22',
                'reset_all': '0',
                'reset': '0'},
        }

        # Format string for full color code.
        self.codeformat = '\033[{}m'
        self.codefmt = lambda s: self.codeformat.format(s)

        # Shortcuts to most used functions.
        self.bold = self.colorbold
        self.normal = self.colornormal
        self.word = self.colorword
        self.ljust = self.wordljust
        self.rjust = self.wordrjust

    def color_code(self, fore=None, back=None, style=None):
        """ Return the code for this style/color
            Fixes style positions so a RESET doesn't affect a following color.
        """

        codes = []
        userstyles = {'style': style, 'back': back, 'fore': fore}
        for stype in userstyles:
            style = userstyles[stype].lower() if userstyles[stype] else None
            # Get code number for this style.
            code = self.codes[stype].get(style, None)
            if code:
                # Reset codes come first (or they will override other styles)
                if style in ('none', 'normal', 'reset', 'reset_all'):
                    codes.insert(0, self.codefmt(code))
                else:
                    codes.append(self.codefmt(code))
        return ''.join(codes)

    def colorize(self, text=None, fore=None, back=None, style=None):
        """ Return text colorized.
            fore,back,style  : Name of fore or back color, or style name.
        """
        if text is None:
            text = ''
        return '{codes}{txt}'.format(codes=self.color_code(style=style,
                                                           back=back,
                                                           fore=fore),
                                     txt=text)

    def colorbold(self, text=None, fore=None, back=None):
        """ Shorthand for style='bright' """
        return self.colorword(text=text, fore=fore, back=back, style='bright')

    def colornormal(self, text=None):
        """ Shorthand for fore, back, = 'normal', 'normal' """
        s = 'reset'
        return self.colorword(text=text, fore=s, back=s, style=s)

    def colorword(self, text=None, fore=None, back=None, style=None):
        """ Same as colorize, but adds a style->reset_all after it. """
        if text is None:
            text = ''
        colorized = self.colorize(text=text, style=style, back=back, fore=fore)
        s = '{colrtxt}{reset}'.format(colrtxt=colorized,
                                      reset=self.color_code(style='reset_all'))
        return s

    def wordljust(self, text=None, length=0, char=' ', **kwargs):
        """ Color a word and left justify it.
            Regular str.ljust won't work properly on a str with color codes.

            Arguments:
                text    : text to colorize.
                length  : overall length after justification.
                char    : character to use for padding. Default: ' '

            Keyword Arguments:
                fore, back, style : same as colorizepart() and word()
        """
        if text is None:
            text = ''
        spacing = char * (length - len(text))
        colored = self.word(text=text, **kwargs)
        return '{}{}'.format(colored, spacing)

    def wordrjust(self, text=None, length=0, char=' ', **kwargs):
        """ Color a word and right justify it.
            Regular str.rjust won't work properly on a str with color codes.
            Arguments:
                text    : text to colorize.
                length  : overall length after justification.
                char    : character to use for padding. Default: ' '

            Keyword Arguments:
                fore, back, style : same as colorizepart() and word()
        """
        if text is None:
            text = ''
        spacing = char * (length - len(text))
        colored = self.word(text=text, **kwargs)
        return '{}{}'.format(spacing, colored)

# Set global ColorCodes instance and helper functions.
colors = ColorCodes()
color = colors.word
colordebug = lambda s: color(text=s, fore='green')
colorindex = lambda i: color(text=str(i), fore='blue', style='bright')
colorimp = lambda s: color(text=str(s), fore='magenta', style='bright')
colorerr = lambda s: color(text=s, fore='red', style='bright')
colorkey = lambda s: color(text=s, fore='blue', style='bright')
colorval = lambda s: color(text=s, fore='green')


class ColorDocoptExit(SystemExit):

    """ Custom DocoptExit class, colorizes the help text. """

    usage = ''

    def __init__(self, message=''):
        usagestr = '{}\n{}'.format(message,
                                   coloredhelp(self.usage)).strip()
        SystemExit.__init__(self, usagestr)


def coloredhelp(s):
    """ Colorize the usage string for docopt
        (ColorDocoptExit, docoptextras)
    """
    newlines = []
    bigindent = (' ' * 16)
    for line in s.split('\n'):
        if line.strip('\n').strip().strip(':') in ('Usage', 'Options'):
            # label
            line = color(line, fore='none', style='bold')
        elif (':' in line) and (not line.startswith(bigindent)):
            # opt,desc line. colorize it.
            lineparts = line.split(':')
            opt = lineparts[0]
            val = lineparts[1] if len(lineparts) == 2 else lineparts[1:]

            # colorize opt
            if ',' in opt:
                opts = opt.split(',')
            else:
                opts = [opt]
            optstr = ','.join([color(o, fore='blue') for o in opts])

            # colorize desc
            valstr = color(val, fore='green')
            line = ':'.join([optstr, valstr])
        elif line.startswith(bigindent):
            # continued desc string..
            line = color(line, fore='green')
        elif (not line.startswith('    ')):
            # header line.
            line = color(line, fore='red', style='bold')
        else:
            # everything else, usage mainly.
            line = line.replace(SCRIPT, color(SCRIPT, fore='green'))

        newlines.append(line)
    return '\n'.join(newlines)


def docoptextras(help, version, options, doc):
    if help and any((o.name in ('-h', '--help')) and o.value for o in options):
        print(coloredhelp(doc).strip("\n"))
        sys.exit()
    if version and any(o.name == '--version' and o.value for o in options):
        print(color(version, fore='blue'))
        sys.exit()

# Override default docopt stuff
docopt.DocoptExit = ColorDocoptExit
docopt.extras = docoptextras


class TodoItem(object):

    """ A single item in the todo list.
        It has some text, and other item-related properties.
    """
    # This marks an item as important when in string format.
    important_str = '** '

    def __init__(self, text=None, important=False):
        self.text = '' if text is None else text
        self.important = important
        # Items with the important_str override the important kwarg.
        if self.text.startswith(TodoItem.important_str):
            self.important = True
            self.text = self.text[len(TodoItem.important_str):]

    def __bool__(self):
        return bool(self.text)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return self.tostring(color=True)

    def to_json(self):
        """ JSON-friendly str representation. No color, using text-markers. """
        return self.tostring(color=False, usetextmarker=True)

    def tostring(self, color=False, usetextmarker=False):
        """ String repr of this item. It's basically just the .text for the
            item. If it is an important item and color=True,
            important items are color-coded (for terminal).
            If usetextmarker is True, the important_str will be prepended
            to important items.
        """
        if not self.text:
            return ''

        usestr = self.text
        if usetextmarker and self.important:
            usestr = '{}{}'.format(TodoItem.important_str, usestr)

        if color:
            return colorimp(usestr) if self.important else usestr
        return usestr


class TodoKey(UserList):

    """ A single key in the todo list. Holds items with indexes. """
    # The key to use when no key is given. (null/None)
    # This is set to a default when TodoList.load_data() is finished.
    # The top key is used as the default when the list is not empty.
    null = 'No Label'

    class __NoLabel(object):  # noqa

        def __bool__(self):
            return False

    def __init__(self, *args, **kwargs):
        label = kwargs.get('label', TodoKey.__NoLabel())
        # Empty label values default to TodoKey.null.
        self.label = label if label else TodoKey.null
        try:
            # Label kwarg was given. Pop it so it doesn't interfere with
            # UserList.__init__()
            kwargs.pop('label')
        except KeyError:
            pass

        super().__init__(*args, **kwargs)
        printdebug('TodoKey(label=\'{}\')'.format(self.label))

    def __bool__(self):
        return bool(self.data)

    def __repr__(self):
        lines = ['{}:'.format(colorkey(self.label))]
        for index, item in enumerate(self.data):
            lines.append('    {}: {}'.format(index, str(item)))

        return '\n'.join(lines)

    def __str__(self):
        return self.__repr__()

    def add_item(self, item, important=False):
        """ Add an item to this key. """
        printdebug('TodoKey."{}".add_item(\'{}\')'.format(self.label, item))
        if isinstance(item, TodoItem):
            newitem = item
        else:
            newitem = TodoItem(text=str(item), important=important)
        self.data.append(newitem)
        return newitem

    def find_item(self, query):
        """ Find an item by its index or regex pattern/text.
            If there is a match, return (index, TodoItem())
            Otherwise, return (None, None)
            * Indexes are zero-based.
        """
        intval, querypat = TodoKey.parse_query(query)
        for index, item in enumerate(self.data):
            if (intval is not None) and (intval == index):
                return index, item
            itemtext = item.tostring(color=False)
            if (querypat is not None) and querypat.search(itemtext):
                return index, item
        return (None, None)

    def get_count(self):
        """ Wrapper for len(self.data) or len(self).
            This is only here to be consistent with TodoList.
            len(TodoList) gives you the amount of keys,
            where TodoList.get_count() gives you the TodoItem count.
            TodoKey.get_count() actually does the same as len(TodoKey).
        """
        return len(self.data)

    def move_item(self, query, newindex):
        """ Move an item from one position to another.
            The query is just as in find_item(), an index or regex/text.
            The new index must be an integer, and must be within the bounds
            of the list.
            Returns (oldindex, newindex, TodoItem) on success.
            Returns (None, None, None) on failure.
            Possibly raises TodoList.BadIndexError or TodoList.SameIndexError.
        """
        index, item = self.find_item(query)
        if index is None:
            return (None, None, None)

        try:
            newindex = int(newindex)
        except (TypeError, ValueError) as exint:
            raise TodoList.BadIndexError(str(exint)) from exint

        maxlength = self.get_count() - 1
        if newindex == index:
            raise TodoList.SameIndexError('Indexes cannot be the same.')
        elif (0 > newindex) or (newindex > maxlength):
            raise TodoList.BadIndexError('Index must be within the bounds.')

        try:
            # Remove the item, and reinsert it into the new index.
            removed = self.data.pop(index)
            self.data.insert(newindex, removed)
        except Exception as ex:
            # Format all lowercase error messages ('list index out of range')
            errmsg = str(ex).capitalize()
            if not errmsg.endswith('.'):
                errmsg = '{}.'.format(errmsg)
            raise TodoList.BadIndexError(errmsg) from ex

        return (index, newindex, item)

    @classmethod
    def parse_query(cls, query):
        """ Parse a search/find query. Returns either:
            (int index, None), (None, Regex Pattern)
            or on error, raises TodoList.BadQueryError().
        """
        try:
            intval = int(query)
            querypat = None
        except (TypeError, ValueError):
            intval = None
            try:
                querypat = re.compile(query, re.IGNORECASE)
            except re.error as exreg:
                errmsg = 'Invalid query: {}\n{}'.format(query, exreg)
                raise TodoList.BadQueryError(errmsg)
        return intval, querypat

    def remove_item(self, query):
        """ Removes an item from this key. The query can be the index,
            or a regex pattern/text to match.
            Returns the removed TodoItem, or None (if not found).
        """
        matchindex, matchitem = self.find_item(query)
        removed = None
        if (matchindex is not None) and (matchitem is not None):
            removed = self.data.pop(matchindex)
        return removed

    def remove_items(self, query):
        """ Removes several items that match an index or regex pattern/text.
            Returns a list of the removed TodoItems, or [].
        """
        removed = []
        for index, item in self.search_items(query):
            removeditem = self.data.pop(index)
            if removeditem:
                removed.append(item)
        return removed

    def search_items(self, query, firstonly=False):
        """ Search all items, return all that match the query.
            Query is the index, or regex pattern (like find_item()).
            If firstonly is True, returns [(firstindex, firstmatch)]
            Without firstonly, returns [(index, match)].
            If no matches are found, returns [].
        """
        if firstonly:
            firstindex, firstmatch = self.find_item(query)
            if (firstindex is not None) and (firstmatch is not None):
                return [(firstindex, firstmatch)]
            return []
        # Find multiple matches.
        intval, querypat = TodoKey.parse_query(query)
        found = []
        for index, item in enumerate(self.data):
            itemtext = item.tostring(color=False)
            if (intval is not None) and (intval == index):
                found.append((index, item))
            elif (querypat is not None) and querypat.search(itemtext):
                found.append((index, item))

        return found

    def to_dict(self):
        """ Turn this key into a dict of {index: TodoItem} """
        return {i: itm for i, itm in enumerate(self.data)}

    def to_json(self):
        """ Turn this key into JSON data. Uses zero-based indexes. """
        # Add key name for final JSON format.
        try:
            jsondata = json.dumps(self.to_json_obj(), sort_keys=True, indent=4)
        except ValueError:
            errmsg = 'Unable to translate key to JSON: {}'.format(self.label)
            raise TodoList.ParseError(errmsg)
        return jsondata

    def to_json_obj(self):
        """ Turn this key into a JSON-friendly dict object. """
        # Convert TodoItems() to str for JSON, and add key name.
        return {
            self.label: {
                i: itm.to_json() for i, itm in self.to_dict().items()
            }
        }


class TodoList(UserDict):

    """ A todo list with keys, the default key being TodoKey.null. """
    class AddError(ValueError):
        pass

    class BadIndexError(IndexError):
        pass

    class BadQueryError(Exception):
        pass

    class LoadError(Exception):
        pass

    class NoFileExists(Exception):
        pass

    class ParseError(Exception):
        pass

    class SameIndexError(BadIndexError):
        pass

    class SaveError(Exception):
        pass

    def __init__(self, *args, **kwargs):
        filename = kwargs.get('filename', None)
        if filename is None:
            self.filename = None
        else:
            self.filename = filename
            kwargs.pop('filename')
        # Make TodoList.data available, intialize like any other dict.
        super().__init__(*args, **kwargs)
        if self.filename is not None:
            self.load_file(self.filename)

    def __bool__(self):
        return bool(self.data)

    def add_item(self, text, key=None, important=False):
        """ Add an item, with an option to save under a certain key.
            Returns (TodoKey, TodoItem) on success.
        """
        if not text:
            raise TodoList.AddError('No item to add.')
        key = key or TodoKey.null
        printdebug('TodoList.add_item(\'{}\', key=\'{}\')'.format(text, key))
        # Find the existing key, or create a new one.
        existing = self.get_key(key, default=TodoKey(label=key))
        # Create the new TodoItem.
        newitem = existing.add_item(item=text, important=important)
        # Save the new items to this key.
        self.data[key] = existing
        return (existing, newitem)

    def clear(self):
        """ Clears all items without warning. """
        self.data = {}
        return True

    def find_item(self, query, key=None):
        """ Finds a specific item in the list.
            The query can be a regex pattern (str), or an index.
            If 'key' is not set, TodoKey.null is used.
            Returns (Keyname, Index, TodoItem()) on success.
            Returns (Keyname, None, None) if no result is found.
            Returns (None, None, None) if no key could be found.
        """
        key = key or TodoKey.null

        todokey = self.get_key(key, None)
        if todokey is None:
            return (None, None, None)

        index, item = todokey.find_item(query)
        return (todokey.label, index, item)

    def get_count(self):
        """ Get an overall count of items in all keys.
            To get just the key count, len(TodoList) works.
        """
        total = 0
        for todokey in self.todokeys():
            total += len(todokey)
        return total

    def get_key(self, key=None, default=None):
        """ Returns raw format items from a key.
            If no key exists, returns None.
            Case insensitive.
        """
        if isinstance(key, TodoKey):
            # A valid TodoKey was passed in already.
            return key

        key = key or TodoKey.null
        key = key.lower()
        printdebug('TodoList.get_key(\'{}\')'.format(key))
        for todokeyname in self.data:
            todokey = self.data[todokeyname]
            if todokey.label.lower() == key:
                return todokey
        return default

    @staticmethod
    def is_null_str(s):
        """ Return true if this string is a placeholder for None/null. """
        if s:
            nulls = ('', 'null', 'none', 'no label')
            return str(s).lower() in nulls
        return True

    def keynames(self):
        """ Shortcut to sorted(TodoList.data.keys()) """
        return sorted(self.keys())

    def keys(self):
        """ Shortcut to TodoList.data.keys() """
        return self.data.keys()

    def load_data(self, data, append=False):
        """ Load items from a dict. """
        printdebug('Loading data:', data=data)
        if not data:
            # No data passed in!
            self.data = {}
            return 0

        for keyname in sorted(data):
            keyitems = data[keyname]
            todokey = TodoKey(label=keyname)
            if isinstance(keyitems, dict):
                for itemkey in sorted(keyitems):
                    text = keyitems[itemkey]
                    todokey.add_item(item=text)
            elif isinstance(keyitems, list):
                for text in keyitems:
                    todokey.add_item(item=text)
            self.data[keyname] = todokey

        # Set the default key to the first key found, if there is data
        # available.
        if self.data:
            TodoKey.null = self.keynames()[0]
            msgnullsetting = 'TodoKey.null = \'{}\''.format(TodoKey.null)
            printdebug('TodoList.load_data(): {}'.format(msgnullsetting))

        return self.get_count()

    def load_file(self, filename=None):
        """ Load items from a json file. """
        if not filename:
            filename = self.filename
        if not filename:
            raise TodoList.LoadError('No filename provided.')

        if not os.path.exists(filename):
            errmsg = 'File doesn\'t exist: {}'.format(filename)
            raise TodoList.NoFileExists(errmsg)

        try:
            with open(filename, 'r') as f:
                rawdata = f.read()
        except EnvironmentError as exread:
            errmsg = 'Unable to read: {}'.format(filename)
            raise TodoList.LoadError(errmsg) from exread

        if not rawdata.strip():
            # Empty file.
            return self.load_data({})

        try:
            jsonobj = json.loads(rawdata)
        except (TypeError, ValueError) as exparse:
            errmsg = 'Unable to parse JSON from: {}'.format(filename)
            raise TodoList.ParseError(errmsg) from exparse

        if isinstance(jsonobj, list):
            # Convert old todo data to new format.
            converted = {TodoKey.null: {}}
            converted[TodoKey.null] = {i: s for i, s in enumerate(jsonobj)}
            return self.load_data(converted)

        return self.load_data(jsonobj)

    def move_item(self, query, newindex, key=None):
        """ Move an item from one position to another in it's own key.
            see: TodoKey.move_item()
            Returns (TodoKey, oldindex, newindex, TodoItem) on success.
            Returns (None, None, None, None) on failure.
            Possibly raises TodoList.BadIndexError, TodoList.SameIndexError
        """
        key = key or TodoKey.null
        todokey = self.get_key(key, None)
        if todokey is None:
            return (None, None, None, None)

        oldindex, newindex, item = todokey.move_item(query, newindex)
        return (todokey, oldindex, newindex, item)

    def move_item_tokey(self, query, newkey, key=None):
        """ Moves an item from one group to another.
            Returns (oldTodoKey, newTodoKey, TodoItem) on success.
            Returns (None, None, None) on failure.
        """
        key = key or TodoKey.null
        todokey = self.get_key(key, None)
        if todokey is None:
            return (None, None, None)
        printdebug('TodoList.move...key(\'{}\', \'{}\')'.format(query, newkey))
        removed = todokey.remove_item(query)
        printdebug('TodoList.move_item_tokey: moving {}'.format(removed))
        if removed is None:
            return (None, None, None)

        newkey, newitem = self.add_item(removed, key=newkey)
        return (todokey, newkey, newitem)

    def remove_item(self, query, key=None):
        """ Remove an item from the todo list.
            If no key is given, then TodoKey.null is used.
            If the item was successfully removed, it is returned.
            Returns None on failure.
        """
        key = key or TodoKey.null
        todokey = self.get_key(key, None)
        if todokey is None:
            return None
        removed = todokey.remove_item(query)
        return removed

    def rename_key(self, newkeyname, key=None):
        """ Rename a key. Old key defaults to TodoKey.null """
        key = key or TodoKey.null
        try:
            removed = self.data.pop(key)
        except KeyError:
            return None
        removed.label = newkeyname
        self.data[newkeyname] = removed
        return self.get_key(newkeyname)

    def save_file(self, filename=None):
        """ Save items to file. """
        if not filename:
            filename = self.filename
        if not filename:
            raise TodoList.SaveError('No filename provided.')

        # make json string.
        jsondata = self.to_json()

        # write to file.
        try:
            with open(filename, 'w') as f:
                f.write(jsondata)
        except EnvironmentError as exwrite:
            errmsg = 'Unable to write to file: {}'.format(filename)
            raise TodoList.SaveError(errmsg) from exwrite
        return self.get_count()

    def search_items(self, query, firstonly=False):
        """ Searches ALL items that match the query.
            The query can be a regex pattern (str), or an index.
            This may return multiple results.
            If 'firstonly' is True, then only the first result is returned.
            Returns [results] on success (even if first only is used.)
                where results are: [(KeyName, [(Index, TodoItem)])]
            Returns [] when no match is found.
        """
        results = []
        for keyname in self.keynames():
            todokey = self.get_key(keyname)
            founditems = todokey.search_items(query)
            if founditems:
                if firstonly:
                    return [(keyname, founditems)]
                results.append((keyname, founditems))
        return results

    def to_json(self, usedict=False):
        """ Return the json string for this todo list. """
        d = {}
        for keyname, todokey in self.data.items():
            # Keys can be represented as dicts or lists.
            d[keyname] = {} if usedict else []
            if usedict:
                # Use the old dict format for items.
                for index, item in todokey.to_dict().items():
                    itemtext = item.tostring(color=False, usetextmarker=True)
                    d[keyname][index] = itemtext
            else:
                # Use a simple list for items.
                for item in todokey.data:
                    itemtext = item.tostring(color=False, usetextmarker=True)
                    d[keyname].append(itemtext)

        try:
            jsondata = json.dumps(d, indent=4, sort_keys=True)
        except (TypeError, ValueError) as exjson:
            errmsg = 'Unable to generate JSON from: {!r} \n{}'.format(
                d,
                exjson)
            raise TodoList.ParseError(errmsg)
        return jsondata

    def todokeys(self):
        """ Shortcut to TodoList.data.values() """
        return list(self.data.values())

# Start of script ---------------------------------------------------
if __name__ == '__main__':
    mainret = main(docopt.docopt(USAGESTR, version=VERSIONSTR))
    sys.exit(mainret)
