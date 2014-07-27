Todo
====

Yet another todo app. :)

This one is written in Python, is for linux (color codes are used), and
allows you to group items with 'keys'.

The file is saved as JSON, so it is hand-editable. It uses a dict/map to store
items in their own 'group' (hence the 'keys').

Usage:
------

Add an item to the default key:

    todo "Get groceries."

Move that todo item to a new group/another group:

    todo -m 0 "In Town"

0 is the index of the item, you can also use:

    todo -m "Get groc" "In Town"
    # ...because it is looking for an index, regex pattern, or text.

At this point there is only 1 'key', so you don't have to name the key.

If we add another key then we may need to specify:

    todo "New Key" "My new item"

Now we have 2 keys, they are alphabetically sorted and if you don't
specify a key, the top one is used.

You can mark that item as important (color the item purple):

    todo -i "New Key" "^My"
    # Regex was used there to find the item. The first item found is picked.

You can rename a key:

    todo -n "New Key" "important stuff"

You can remove a key and all of its items. If a key has more than one
item, confirmation is needed.

    todo -K "important stuff"

To list all of your items just run `todo`.

To list only a single key:

    todo -l "important stuff"


You can move items to new positions in the same key by index or name
('top', 'bottom', 'down', 'up'). You can move an item to another key.
You can mark them as important or unimportant, print the list as JSON to
stdout, or search for items using regex/text/indexes.

I wrote this for myself and set it to run when BASH loads an interactive
session. This way I am reminded of my todo list often. If it is useful to
other people then great. Take it, change it, use it, whatever.
