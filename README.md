Todo
====

Yet another todo app. :)

This one is written in Python, is for linux (color codes are used), and
allows you to group items with 'keys'.

File Format:
------------

The file is saved as JSON, so it is hand-editable. It uses a `dict` to store
items in their own 'group' (hence the 'keys'). By default, a single global list
is saved in the same directory as `todo.py`. You can use multiple files by
creating a `todo.lst` in whatever directory you are running `todo.py` from.
An example would be putting a `todo.lst` in your project directory to track
your goals or bugs. The list would only be used when running `todo.py` from
your project directory.

    $ cd /my/project; pwd
    /my/project
    $ touch todo.lst
    $ todo
    Todo list loaded from: /my/project/todo.lst (Empty)

    $ cd ..
    $ # Using the global todo list.
    $ todo
    Todo list loaded from: /path/to/todo/todo.lst (Empty)

It always tells you which file you are working with.

List Manipulation:
--------------

When looking up an item you can use it's index, text, or a regular expression.
It will let you know when more than one item matches.

You can move items to new positions in the same key by index or name
('top', 'bottom', 'down', 'up'). You can move an item to another key. You can
remove items or keys.
You can mark them as important or unimportant, print the list as JSON to
stdout, or search for items using regex/text/indexes.


Example Usage:
--------------

I suggest you create a symlink to it to somewhere in your `$PATH` like this:

    # Local
    ln -s /path/to/todo.py /home/username/.local/bin/todo

    # Global
    sudo ln -s /path/to/todo.py /usr/bin/todo



Here are some of the most common uses for todo:

* Add an item:

        todo 'Go to the store'

* Add an item with a label/key:

        todo coding 'Debug that thing.'

* Rename a key. (*`-n` or `--renamekey`*):

        todo --renamekey 'No Label' all

* Remove a key. (*`-K` or `--removekey`*):

        todo --removekey 'No Label'

* Move an item to another key. (*`-m` or `--movetokey`*):

        todo --movetokey 'Debug that' 'My key'

* Add an important item, colored bold and bright when listed.

    (*`-a -i`*) or (*`--add --important`*):

        todo -ai coding 'Refactor the mess.'

* Mark an existing item important:

        todo -i coding 'Debug that'

* Mark an important item unimportant. (*`-I` or `--unimportant`*):

        todo -I coding 'Debug that'

* List all items (*`-L` or no arguments*):

        todo

* List all items in a single key (*`-l [key]` or  just the key name*):

        todo coding

* Print items in JSON format. (*`-j` or `--json`*):

        todo --json



Command-Line Options:
--------------------

There are many options to let you create, remove, position, prioritize, and
group todo items. You don't have to use all of these to work with `todo`.

A simple `todo 'new item'` will work to get started. To remove it use
`todo -r 'new'`.

```
Usage:
    todo -h | -v
    todo [-a | -b | -d | -i | -r | -R | -s | -t | -u] KEY ITEM
         [-f filename] [-D]
    todo [-a | -b | -d | -i | -r | -R | -s | -t | -u] ITEM
         [-f filename] [-D]
    todo [-c | -j]                  [-f filename] [-D]
    todo -a [-i] KEY ITEM           [-f filename] [-D]
    todo -a [-i] ITEM               [-f filename] [-D]
    todo -e FILE KEY                [-f filename] [-D]
    todo -I KEY ITEM                [-f filename] [-D]
    todo -I ITEM                    [-f filename] [-D]
    todo -K KEY                     [-f filename] [-D]
    todo -l [KEY]                   [-f filename] [-D]
    todo -L                         [-f filename] [-D]
    todo -m KEY ITEM <new_key>      [-f filename] [-D]
    todo -m ITEM <new_key>          [-f filename] [-D]
    todo -n [KEY] <new_keyname>     [-f filename] [-D]
    todo -p KEY ITEM <new_position> [-f filename] [-D]
    todo -p ITEM <new_position>     [-f filename] [-D]

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
    -e FILE,--export FILE  : Export a single key's items as JSON.
                             FILE should be the file name for an existing
                             JSON file, or a new file to be created.
                             If '-' is passed, data will be printed to
                             stdout.
    -f FILE,--file FILE    : Use this input file instead of todo.lst.
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
    -m,--movetokey         : Move item to a new key, or another key.
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
```


Library:
--------

`todo.py` is importable.

The library contains a `TodoList` class that holds `TodoKey`s which in turn
holds `TodoItem`s. Each have their own methods for working with them. I won't
document them here, but the source is documented if you want to read it.
I'll just say that they have all of the functions you would expect out of a
Todo library:

    todolist = TodoList('todo.lst')
    todolist.add_item('foo', key=None, important=False)
    todolist.remove_item('foo', key=None)
    keylabel, itemindex, item = todolist.find_item(query, key=None)
    print(todolist.to_json())

    todokey = todolist.get_key('No Label')
    if todokey is None:
        print('No key with that name.')
        exit()

    print(str(todokey))

    index, todoitem = todokey.find_item('foo')
    if todoitem:
        print(str(todoitem))
        # Better str()
        print(todoitem.tostring(color=True))

    ...and the others (remove, search, move, etc.)

The `TodoList` class and friends do not `print` anything. Exceptions are
raised when problems are encountered.
There are some custom exception classes used, based on `Exception`,
`IndexError`, and `ValueError`.
Methods are documented with which errors they are known to raise.


Screenshot:
-----------

![todo](http://welbornprod.com/static/images/todo/todo-example.png)


I wrote this for myself and I actually use it a lot. I set it to run when BASH
loads an interactive session. This way I am reminded of my todo list often.
If it is useful to other people then great.
Take it, change it, use it, whatever.
