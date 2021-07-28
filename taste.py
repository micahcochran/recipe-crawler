#!/usr/bin/env python3

import json
import platform
import pprint
import sys


def usage():
    prompt = "$"
    if platform.system() == "Windows":
        prompt = "C:\..>"

    usage_msg = f"""
Tool for tasting (inspecting) a JSON cookbook.
    {prompt} taste.py [cookbook.json] [attribute]
        List [attribute] in all the recipes.  Returns None if unavailable

    {prompt} taste.py [cookbook.json] [number]
        List the entire JSON of the recipe at that index [number] 
        (Note: index begins at zero)

    {prompt} taste.py [cookbook.json] attrs
        List the attributes.

    {prompt} taste.py [cookbook.json] length
        Display the number of recipes in the cookbook.        
    """
    return usage_msg


if __name__ == "__main__":
    pp = pprint.PrettyPrinter()
    if len(sys.argv) < 3:
        print(usage())
        sys.exit(0)

    with open(sys.argv[1], "r") as fp:
        cookbook = json.load(fp)

    if sys.argv[2] == "attrs":
        attrs = set()
        for recipe in cookbook:
            attrs = attrs.union(tuple(recipe.keys()))

        attr_str = ", ".join(attrs)
        # TODO: print this nicer
        pp.pprint(f"Attributes:  {attrs}")
        sys.exit(0)
    elif sys.argv[2] == "length":
        print(f"Number of recipes in cookbook: {len(cookbook)}")
        sys.exit(0)

    if sys.argv[2].isdigit() is True:
        idx = int(sys.argv[2])
        if idx >= len(cookbook):
            print(f"Cookbook only has {len(cookbook)} recipes.  Try a smaller number.")
            sys.exit(1)
        elif idx < 0:
            print(
                f"Negative numbered recipes are not valid input. The number of recipes starts at 0."
            )
            sys.exit(1)

        pp.pprint(cookbook[idx])
        sys.exit(0)

    results = [recipe.get(sys.argv[2]) for recipe in cookbook]
    pp.pprint(results)
