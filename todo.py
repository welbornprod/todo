#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" todo.py
    ...A revamp of my quick and dirty todo list app.
    -Christopher Welborn 07-21-2014
"""
# TODO: New remove/move operations should work on multiple key items.
#       Right now they only work on 1 item per key, because of
#       TodoKey.find_item()

# TODO: A namedtuple() may help with readability for the find_* returns.
#       A dict may also help with parsing and operating on the results.

import inspect
import functools
import json
import os
import re
import shutil
import sys
from collections import UserDict, UserList
from contextlib import suppress

bad_import_msg = '\n'.join((
    'Error: {err}',
    'You may need to install {name} with pip: pip install {package}'
)).format

try:
    from colr import (
        __version__ as colr_version,
        auto_disable as colr_auto_disable,
        color,
        Colr as C,
    )
except ImportError as ex:
    print(bad_import_msg(err=ex, name='Colr', package='colr'))
    sys.exit(1)
try:
    import docopt
except ImportError as ex:
    print(bad_import_msg(err=ex, name='Docopt', package='docopt'))
    sys.exit(1)

NAME = 'Todo'
VERSION = '2.3.4'
VERSIONSTR = '{} v. {}'.format(NAME, VERSION)
SCRIPT = os.path.split(os.path.abspath(sys.argv[0]))[1]
SCRIPTDIR = os.path.abspath(sys.path[0])

USAGESTR = """{versionstr}
    Usage:
        {script} -h | -v
        {script} [-a | -b | -d | -r | -R | -s | -t | -u] KEY ITEM
             [-f filename] [-D]
        {script} [-a | -b | -d | -r | -R | -s | -t | -u] ITEM
             [-f filename] [-D]
        {script} [-c] | ([-j] [KEY])        [-f filename] [-D]
        {script} -a [-i] KEY ITEM           [-f filename] [-D]
        {script} -a [-i] ITEM               [-f filename] [-D]
        {script} -e FILE KEY                [-f filename] [-D]
        {script} -I KEY [ITEM]              [-f filename] [-D]
        {script} -I (KEY | ITEM)            [-f filename] [-D]
        {script} -i KEY [ITEM]              [-f filename] [-D]
        {script} -i (KEY | ITEM)            [-f filename] [-D]
        {script} -K KEY                     [-f filename] [-D]
        {script} -l [KEY]                   [-f filename] [-D]
        {script} (-L | -P)                  [-f filename] [-D]
        {script} -m KEY ITEM <new_key>      [-f filename] [-D]
        {script} -m ITEM <new_key>          [-f filename] [-D]
        {script} -n [KEY] <new_keyname>     [-f filename] [-D]
        {script} -p KEY ITEM <new_position> [-f filename] [-D]
        {script} -p ITEM <new_position>     [-f filename] [-D]

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
        -f FILE,--file FILE    : Use this input file instead of todo.lst.
        -h,--help              : Show this help message.
        -i,--important         : Mark key/item as important (bold/red).
        -I,--unimportant       : Mark key/item as unimportant.
        -j,--json              : Show list, or a specific key in JSON format.
        -K,--removekey         : Remove a key/label. (includes all items)
        -l,--list              : List items from a certain key.
                                 Defaults to: (first key)
        -L,--listall           : List all items from all keys.
                                 This is the default action when no
                                 arguments are given.
        -m,--movetokey         : Move item to a new key, or another key.
        -n,--renamekey         : Give a key another name/label.
        -p,--position          : Move item to a new position in the same
                                 key.
        -P,--preview           : Preview the list. Like --listall, except
                                 some items are cut off.
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


def main(argd):  # noqa
    """ Main entry point, expects doctopt arg dict as argd """
    global DEBUG, todolist, userkey, useritem
    DEBUG = argd['--debug']
    if DEBUGARGS:
        DEBUG = True
        printdebug("Arguments:", data=argd)
        return 0
    printdebug_header()

    # Use provided file, then local, then the default.
    if argd['--file']:
        todofile = argd['--file']
    elif os.path.exists(LOCALFILE):
        todofile = LOCALFILE
    else:
        todofile = DEFAULTFILE

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
    if not argd['--json']:
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
    try:
        retvalue = runaction()
    except Exception as ex:
        printstatus('Error:', error=ex)
        return 1

    # printdebug(text='Todo Items after this run:', data=todolist)
    return retvalue

# Functions -------------------------------------------------------


def build_actions(argdict):
    """ Builds a dict of command-line args mapped to their function,
        arguments are prefilled.
    """
    useritem = argdict['ITEM'] or None
    rawkey = argdict['KEY']
    userkey = rawkey or None
    printdebug('Using key: {!r}'.format(userkey))

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
        '--important': {
            'function': do_mark_important,
            'args': [useritem],
            'kwargs': {
                'key': userkey,
                'adding': argdict['--add'],
                'important': True,
            },
        },
        '--json': {
            'function': do_json,
            'kwargs': {'key': userkey}
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
        '--preview': {
            'function': do_listall,
            'kwargs': {'preview': True},
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
            'kwargs': {
                'key': userkey,
                'important': False,
            },
        },
        '--up': {
            'function': do_move_item,
            'args': [useritem, 'up'],
            'kwargs': {'key': userkey},
        },
    }
    return actions


def check_empty_key(key=None, silentsave=False):
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
            if do_removekey(todokey, silentsave=silentsave) == 0:
                return True
            return False

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


def debug(*args, **kwargs):
    """ Print a message only if DEBUG is truthy. """
    if not (DEBUG and args):
        return None

    # Use stderr by default.
    if kwargs.get('file', None) is None:
        kwargs['file'] = sys.stderr

    # Include parent class name when given.
    parent = kwargs.get('parent', None)
    with suppress(KeyError):
        kwargs.pop('parent')

    # Go back more than once when given.
    backlevel = kwargs.get('back', 1)
    with suppress(KeyError):
        kwargs.pop('back')

    frame = inspect.currentframe()
    # Go back a number of frames (usually 1).
    while backlevel > 0:
        if frame is None:
            raise ValueError('`level` is too large, there is no frame.')
        frame = frame.f_back
        backlevel -= 1
    if frame is None:
        raise ValueError('`level` is too large, there is no frame.')
    fname = os.path.split(frame.f_code.co_filename)[-1]
    lineno = frame.f_lineno
    if parent:
        func = '{}.{}'.format(parent.__class__.__name__, frame.f_code.co_name)
    else:
        func = frame.f_code.co_name

    # Use the colorized lineinfo for printing.
    lineinfo = C('{}:{} {}: '.format(
        C(fname, 'yellow'),
        C(str(lineno).rjust(5), 'blue'),
        C().join(C(func, 'magenta'), '()').rjust(25)
    ))

    # Are we omitting the line info, and just aligning with the end of it?
    align = kwargs.get('align', False)
    with suppress(KeyError):
        kwargs.pop('align')

    # An editable arg list, for patching.
    pargs = list(C(a, 'green').str() for a in args)

    # Is this a continuation from a previous line?
    # Getting this for debug(), re-setting for print().
    kwargs['end'] = kwargs.get('end', '\n')
    willcontinue = (not kwargs['end'].endswith('\n'))
    continued = debug.continued.get(kwargs['file'], False)
    if align or continued:
        debug.continued[kwargs['file']] = willcontinue
        if align:
            pargs[0] = ''.join((' ' * len(lineinfo.stripped()), pargs[0]))
        print(*pargs, **kwargs)
        return None
    debug.continued[kwargs['file']] = willcontinue

    # Patch args to stay compatible with print().
    pargs[0] = ''.join((str(lineinfo), pargs[0]))
    print(*pargs, **kwargs)
# This dict tracks whether line info should be included, based on whether
# the last line's `end` had a newline in it, per file descriptor.
debug.continued = {}


def do_add(text, key=None, important=False):
    """ Add an item to the todo list. (Key is optional.) """
    if not text:
        printstatus('No item to add!', error=True)
        return 1
    printdebug('do_add(key={},important={},"{}")'.format(
        key,
        important,
        text))
    key, newitem = todolist.add_item(text, key=key, important=important)
    # Todo lists are zero-based.
    printstatus(
        'Added item:',
        key=key,
        item=newitem,
        index=len(key) - 1,
    )
    return do_save()


def do_clear():
    """ Clear all items (after confirmation.) """
    itemcnt = todolist.get_count()
    confirmwarn = 'This will clear all {} items from the list.'.format(
        itemcnt)
    confirmmsg = 'Clear the entire todo list?'
    if confirm(confirmmsg, warn=confirmwarn):
        todolist.clear()
        return do_save()

    printstatus('User cancelled.', error=True)
    return 1


def do_export(key=None, filename=None):
    """ Export a key, or all keys to another JSON file.
        This will try to safely merge with existing files.

        Arguments:
            key       : TodoKey to export.
            filename  : Existing or new JSON file name. Content will be
                        printed to stdout if '-' is given.
    """
    todokey = get_key(key or TodoKey.null)
    if todokey is None:
        return 1
    if filename in (None, '-'):
        print(todokey.to_json())
        return 0

    printstatus('Merging key into {}:'.format(filename), key=todokey)
    return 0 if merge_json(todokey.to_json_obj(), filename) else 1


def do_json(key=None):
    """ Print JSON format of TodoList. """
    if key:
        return do_export(key=key)

    try:
        jsondata = todolist.to_json()
    except TodoList.ParseError:
        printstatus('Unable to format JSON!', error=True)
        return 1

    print(jsondata)
    return 1


def do_listall(preview=False):
    """ List all items in all keys. """
    retall = 0
    names = todolist.keynames()
    for keyname in names:
        ret = do_listkey(keyname, preview=preview)
        if ret == 1:
            retall = 1
            printstatus('Error listing key:', key=keyname, error=True)
    if not names:
        msg = color('No items saved yet.', fore='red')
        print('\n{}\n'.format(msg))
    return retall


def do_listkey(key=None, preview=False):
    """ List all items within a key. """
    todokey = get_key(key or TodoKey.null)

    if todokey is None:
        return 1

    if todokey:
        keystr = todokey.preview_str() if preview else str(todokey)
        print('    {}'.format(keystr.replace('\n', '\n    ')))
    else:
        print('    {}'.format(str(todokey)))
        printstatus(
            '        (no items in this key)',
            error=True,
            nobreak=True)
    return 0


def do_mark_important(query, key=None, adding=False, important=True):
    """ Mark an existing item as important. The 'adding' flag short-circuits
        this function and does 'do_add' instead. It is because of the way
        arguments are handled (the way functions are fired off.)
    """
    printdebug('Marking important={}: {}, key={}'.format(
        important,
        query,
        key,
    ))
    todokey = todolist.get_key(key, default=None)
    if todokey is None:
        printdebug('Looking for item to mark important={}: {}'.format(
            important,
            key,
        ))
        # User has passed only an item's text. We have to find the key.
        items = todolist.find_item(key)
        if not items:
            printstatus('Cannot find that item: {}'.format(key), error=True)
            return 1
        # TODO: this is very inefficient.
        errs = 0
        for foundkey, _, item in items:
            if adding:
                errs += do_add(item.text, key=foundkey, important=important)
            else:
                errs += do_mark_important(
                    item.text,
                    key=foundkey,
                    important=important
                )
        return errs

    # We have a key, or both a key and an item.
    if adding:
        return do_add(query, key=key, important=important)

    # We should have a useable key name after this, or else everything fails.
    todokey = get_key(key or TodoKey.null)
    if todokey is None:
        return 1

    importantstr = 'important' if important else 'unimportant'
    msg = 'Marked as {}:'.format(importantstr)

    if not query:
        # No query, we are marking a key as important.
        todokey.important = important
        printstatus(msg, key=todokey)
    else:
        index, item = todokey.find_item(query)
        if (index is None) or (item is None):
            printstatus('Unable to find that item:', item=query, error=True)
            return 1
        item.important = important
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
    found = todolist.find_item(query, key=key)
    if not found:
        printstatus('Unable to find that item:', item=query)
        return 1
    errs = 0
    for todokey, index, item in found:
        oldkey, movedkey, item = todolist.move_item_tokey(
            index,
            newkey,
            key=todokey)
        keystr = '{} -> {}'.format(todokey.label, newkey)
        if (oldkey is None) and (newkey is None) and (item is None):
            printstatus('Unable to do move:', key=keystr, item=query)
            errs += 1
        else:
            printstatus('Move item:', key=keystr, item=item)

        if not check_empty_key(oldkey, silentsave=True):
            printdebug('Key still has items: {}'.format(oldkey.label))

    return do_save()


def do_remove(query, key=None, confirmation=True):
    """ Remove an item (if no key is given, the default key is used.) """
    items = todolist.find_item(query, key=key)
    if not items:
        printstatus('Could not find:', key=(key or '(any key)'), item=query)
        if query in todolist.keynames():
            printstatus('Did you mean to use --removekey?')
        return 1

    if confirmation:
        itemlen = len(items)
        warnmsg = '\n'.join((
            'This will remove {cnt} item{plural}:',
            '    {items}')).format(
                cnt=itemlen,
                plural='' if itemlen == 1 else 's',
                items='\n    '.join(
                    '{}: {}'.format(key.label, item.preview_str())
                    for key, _, item in items
                )
        )
        msg = 'Are you sure you want to remove {plural}?'.format(
            plural='this item' if itemlen == 1 else 'these items'
        )
        if not confirm(msg, warn=warnmsg):
            printstatus('User Cancelled', error=True)
            return 1

    for key, index, item in items:
        removed = key.remove_item(index)
        if removed is None:
            printstatus('Could not find:', key=key, item=query)
            return 1
        printstatus('Removed:', key=key, item=removed, index=index)
        # Offer to delete the key if it is empty.
        if not check_empty_key(key, silentsave=True):
            printdebug('Key still has items: {}'.format(key.label))

    return do_save()


def do_removekey(key=None, confirmation=True, silentsave=False):
    """ Remove a key and all of it's items. """
    key = key if key is not None else TodoKey.null
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

    if todolist.delete_key(todokey):
        printstatus('Removed:', key=todokey)
    else:
        printstatus('Unable to remove key:', key=todokey)
    return do_save(silent=silentsave)


def do_renamekey(newkeyname, key=None):
    """ Rename a key. """
    key = key if key is not None else TodoKey.null
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


def do_save(silent=False):
    """ Save all items to disk. """
    itemcount = todolist.save_file()
    if itemcount > 0:
        if not silent:
            printstatus('Items saved:', index=itemcount)
        return 0
    elif itemcount == 0:
        if not silent:
            printstatus('Items saved. (list is blank)')
        return 0

    # Error saving.
    if not silent:
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
                    '({}, {})').format(
                        argname,
                        fname,
                        args,
                        kwarg_str(kwargs))
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
                                color() is called on each item before
                                returning the list.

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
        printdebug('Already a key: {}'.format(keyname.label))
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
            debug(text, back=2)
        if data:
            printobj(data)


def printdebug_header():
    """ Print some debug info about this Todo version, if DEBUG is truthy. """
    printdebug(
        '\n'.join((
            'Using:',
            '      colr: {colr_ver}',
            '    docopt: {docopt_ver}'
            '    python: {py_ver}',
        )).format(
            colr_ver=colr_version,
            docopt_ver=docopt.__version__,
            py_ver='{v.major}.{v.minor}.{v.micro}'.format(v=sys.version_info)
        )
    )


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


def printobj(d, indent=0):  # noqa
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
            error    : Optional Exception, or True for printing error msgs.
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

    print(
        ''.join((
            '' if nobreak else '\n',
            ' '.join(msgfmt).format(**msgfmtargs)
        )),
        file=sys.stderr if error else sys.stdout
    )
    # Print the exception message if it was passed with 'error'.
    if isinstance(error, Exception):
        errmsg = str(error)
        if errmsg:
            print(colorerr(errmsg), file=sys.stderr)


# Classes ---------------------------------------------------------

def colorindex(i):
    return color(text=str(i), fore='blue', style='bright')


def colorimp(s):
    return color(text=str(s), fore='magenta', style='bright')


def colorimpkey(s):
    return color(text=s, fore='yellow', style='bright')


def colorerr(s):
    return color(text=s, fore='red', style='bright')


def colorkey(s):
    return color(text=s, fore='blue', style='bright')


def colorval(s):
    return color(text=s, fore='green')


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
        linestrip = line.strip()
        if linestrip.strip(':') in ('Usage', 'Options'):
            # label
            line = color(line, fore='reset', style='bold')
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
        elif line.startswith(bigindent) and (not linestrip.startswith('[')):
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


def docoptextras(helpstr, version, options, doc):
    if (helpstr and
            any((o.name in ('-h', '--help')) and o.value for o in options)):
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
        return self.to_str(usetextmarker=True)

    def __str__(self):
        return self.to_str(color=True)

    def preview_str(self, color=True, usetextmarker=False):
        """ Return a string containing a "preview" of the item's text. """
        max_itemlen = 75
        return self.to_str(
            color=color,
            usetextmarker=usetextmarker,
            max_length=max_itemlen
        )

    def to_json(self):
        """ JSON-friendly str representation. No color, using text-markers.
        """
        return self.to_str(color=False, usetextmarker=True)

    def to_str(self, color=False, usetextmarker=False, max_length=None):
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

        if max_length:
            usestr = usestr.split('\n')[0][:max_length]
            if len(self.text) > max_length:
                usestr = '{}...'.format(usestr)

        if color:
            return colorimp(usestr) if self.important else usestr
        return usestr


class TodoKey(UserList):

    """ A single key in the todo list. Holds items with indexes. """
    # The key to use when no key is given. (null/None)
    # This is set to a default when TodoList.load_data() is finished.
    # The top key is used as the default when the list is not empty.
    null = 'No Label'
    important_str = '*'

    class __NoLabel(object):  # noqa

        def __bool__(self):
            return False

    def __init__(self, *args, **kwargs):
        label = kwargs.get('label', TodoKey.__NoLabel())
        # Empty label values default to TodoKey.null.
        self.label = label if label else TodoKey.null
        with suppress(KeyError):
            # Label kwarg was given. Pop it so it doesn't interfere with
            # UserList.__init__()
            kwargs.pop('label')
        self.important = kwargs.get('important', False)
        with suppress(KeyError):
            kwargs.pop('important')
        if self.label.startswith(self.important_str):
            self.important = True
            self.label = self.label[len(self.important_str):]

        super().__init__(*args, **kwargs)
        # These will only print when running ./todo.py itself.
        # Otherwise, todo.DEBUG would have to be set.
        # So, by default nothing is ever printed from these classes.
        printdebug('TodoKey(label=\'{}\'), important='.format(
            self.label,
            self.important
        ))

    def __bool__(self):
        return bool(self.data)

    def __repr__(self):
        return self.to_str(usetextmarker=True)

    def __str__(self):
        return self.to_str(color=True)

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
        printdebug('Finding item: {!r}'.format(query))
        intval, querypat = TodoKey.parse_query(query)
        for index, item in enumerate(self.data):
            if (intval is not None) and (intval == index):
                return index, item
            itemtext = item.to_str(color=False)
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

    def get_label(self, color=False, usetextmarker=False):
        """ Retrieve the formatted label for this key. """
        lbl = self.label
        if usetextmarker and self.important:
            lbl = ''.join((self.important_str, lbl))

        if color:
            return colorimpkey(lbl) if self.important else colorkey(lbl)
        return lbl

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
        if (query is None) or (query == ''):
            raise TodoList.BadQueryError('Empty query!')

        try:
            intval = int(query)
            querypat = None
        except (TypeError, ValueError):
            intval = None
            try:
                querypat = re.compile(query, re.IGNORECASE)
            except (re.error, TypeError) as exreg:
                errmsg = 'Invalid query: {}\n{}'.format(query, exreg)
                raise TodoList.BadQueryError(errmsg)
        return intval, querypat

    def preview_str(self):
        """ A short preview list of this key's items. """
        return self.to_str(max_items=2, color=True)

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
            itemtext = item.to_str(color=False)
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
            jsondata = json.dumps(
                self.to_json_obj(),
                sort_keys=True,
                indent=4)
        except ValueError:
            errmsg = 'Unable to translate key to JSON: {}'.format(self.label)
            raise TodoList.ParseError(errmsg)
        return jsondata

    def to_json_obj(self):
        """ Turn this key into a JSON-friendly dict object. """
        # Convert TodoItems() to str for JSON, and add key name.
        printdebug(
            'Converting key to JSON: {}'.format(
                self.get_label(color=True, usertextmarker=True)
            )
        )
        return {
            self.get_label(usetextmarker=True): {
                i: itm.to_json() for i, itm in self.to_dict().items()
            }
        }

    def to_str(self, max_items=None, color=False, usetextmarker=False):
        """ Return a string representation of this key, optionally cutting
            the list off at `max_items`.
        """
        lbl = self.get_label(color=color, usetextmarker=usetextmarker)
        lines = [
            '{}:'.format(lbl)
        ]
        for index, item in enumerate(self.data):
            if max_items and index == max_items:
                break
            lines.append('    {}: {}'.format(
                index,
                item.to_str(color=color, usetextmarker=usetextmarker)
            ))
        else:
            # The entire list was built.
            return '\n'.join(lines)
        # The list was cut short.
        if self.data:
            lines.append(
                '       (plus {} more...)'.format(len(self) - max_items)
            )
        return '\n'.join(lines)


class TodoList(UserDict):

    """ A todo list with keys, the default key being TodoKey.null. """
    class AddError(ValueError):
        pass

    class BadIndexError(IndexError):
        pass

    class BadKeyError(KeyError):
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
        key = key if key is not None else TodoKey.null
        printdebug('TodoList.add_item(\'{}\', key=\'{}\')'.format(text, key))
        # Find the existing key, or create a new one.
        existing = self.get_key(key, default=TodoKey(label=key))
        # Create the new TodoItem.
        newitem = existing.add_item(item=text, important=important)
        # Save the new items to this key.
        self.data[key] = existing
        return (existing, newitem)

    def backup_file(self, filename=None):
        """ Backup existing todo.lst. """
        filename = filename or self.filename
        if not filename:
            raise ValueError('No file name is set.')
        if not os.path.exists(filename):
            printdebug('Cannot backup nonexistant file: {}'.format(filename))
            return False

        backupname = '{}~'.format(filename)
        if os.path.exists(backupname):
            printdebug('Overwriting backup file: {}'.format(filename))

        try:
            shutil.copyfile(filename, backupname)
        except EnvironmentError as ex:
            printdebug('Failed to copy backupfile: {} -> {} ({})'.format(
                filename,
                backupname,
                ex
            ))
            return False
        return True

    def clear(self):
        """ Clears all items without warning. """
        self.data = {}
        return True

    def delete_key(self, key=None):
        """ Delete an entire key from this list.
            The key can be a name, or a TodoKey.
        """
        if key is None:
            return False
        if isinstance(key, TodoKey):
            key = key.label
        try:
            del self.data[key]
        except (TypeError, KeyError) as ex:
            errmsg = 'Unable to remove key: {}\n{}'.format(key, ex)
            raise TodoList.BadKeyError(errmsg)
        return True

    def find_item(self, query, key=None):
        """ Finds a specific item in the list.
            The query can be a regex pattern (str), or an index.
            If 'key' is not set, TodoKey.null is used.
            Returns a list [(TodoKey(), Index, TodoItem()] on success.
            Returns [] if no result is found.
        """
        if key:
            printdebug('Searching key: {}'.format(key))
            todokey = self.get_key(key, None)
            if todokey is None:
                return []

            index, item = todokey.find_item(query)
            if (index is not None) and item:
                return [(todokey, index, item)]
            return []

        printdebug('Searching all keys...')
        found = []
        for todokey in self.todokeys():
            index, item = todokey.find_item(query)
            if (index is not None) and item:
                found.append((todokey, index, item))
        return found

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

        key = key if key is not None else TodoKey.null
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
            return str(s).lower() in ('', 'null', 'none', 'no label')
        return True

    def keynames(self):
        """ Shortcut to sorted(TodoList.data.keys()) """
        return sorted(self.keys())

    def keys(self):
        """ Shortcut to TodoList.data.keys() """
        return self.data.keys()

    def load_data(self, data, append=False):
        """ Load items from a dict. """
        # printdebug('Loading data:', data=data)
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
            self.data[todokey.get_label()] = todokey

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
        key = key if key is not None else TodoKey.null
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
        key = key if key is not None else TodoKey.null
        todokey = self.get_key(key, None)
        if todokey is None:
            return (None, None, None)
        printdebug('TodoList.move...key(\'{}\', \'{}\')'.format(
            query,
            newkey))
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
        key = key if key is not None else TodoKey.null
        todokey = self.get_key(key, None)
        if todokey is None:
            return None
        removed = todokey.remove_item(query)
        return removed

    def rename_key(self, newkeyname, key=None):
        """ Rename a key. Old key defaults to TodoKey.null """
        key = key if key is not None else TodoKey.null
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
        # Backup any existing todo.lst.
        self.backup_file(filename=filename)

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
        for todokey in self.data.values():
            # Keys can be represented as dicts or lists.
            jsonkey = todokey.get_label(color=False, usetextmarker=True)
            d[jsonkey] = {} if usedict else []
            if usedict:
                # Use the old dict format for items.
                for index, item in todokey.to_dict().items():
                    itemtext = item.to_str(color=False, usetextmarker=True)
                    d[jsonkey][index] = itemtext
            else:
                # Use a simple list for items.
                for item in todokey.data:
                    itemtext = item.to_str(color=False, usetextmarker=True)
                    d[jsonkey].append(itemtext)

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
    # Disable colors when piping output.
    colr_auto_disable()

    mainret = main(docopt.docopt(USAGESTR, version=VERSIONSTR))
    sys.exit(mainret)
