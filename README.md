Todo
====

Yet another todo app. :)

This one is written in Python, is for linux (color codes are used), and
allows you to group items with 'keys'.

The file is saved as JSON, so it is hand-editable. It uses a dict/map to store
items in their own 'group' (hence the 'keys').

The original `todo` just saved a list as JSON, and consisted of ~350 lines
that were not reusable. So I decided to add some functionality, and turn it
into an `import`able library that also serves as a working app. It has not
been fully tested, and the library has only been used in the app itself.

The library contains a `TodoList` class that holds `TodoKey`s which in turn
holds `TodoItem`s. Each have their own methods for working with them. I won't
document them here, because this is really just a glorified script. I'll just
say that they have most of the functions you would expect out of a Todo
library:

    TodoList.add_item(item, key=None, important=False)
    TodoList.remove_item(query, key=None)
    TodoKey.find_item(query)
    TodoList.find_item(query, key=None)
    str(TodoItem())
    str(TodoKey())
    TodoList.to_json()
    ...and the others (remove, search, move, etc.)


Usage:
------

There are many options. I tried to make it as intuitive as possible. I won't
list them all here, but I will show you the basic usage.

    # Add an item
    todo 'Go to the store'

    # Add an item with a label/key.
    todo coding 'Debug that thing.'

    # Rename a key.
    todo --renamekey 'No Label' all

    # Move an item to another key.
    todo --movetokey 'Debug that' all

    # Add an important item (colored bold and bright when listed)
    todo -ai coding 'Refactor the mess.'

    # Mark an existing item important.
    todo -i coding 'Debug that'

    # List all items.
    todo

    # List all items in a key.
    todo coding

Screenshot:
-----------

![todo](http://welbornprod.com/static/images/todo/todo-example.png)

When looking up an item you can use it's index, text, or a regular expression.
It will let you know when more than one item matches.

You can move items to new positions in the same key by index or name
('top', 'bottom', 'down', 'up'). You can move an item to another key.
You can mark them as important or unimportant, print the list as JSON to
stdout, or search for items using regex/text/indexes.

I wrote this for myself and I actually use it a lot. I set it to run when BASH
loads an interactive session. This way I am reminded of my todo list often.
If it is useful to other people then great.
Take it, change it, use it, whatever.
