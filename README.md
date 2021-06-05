## recipe-crawler.py
This is a web crawler creates a cookbook from recipes found on a few websites.  
The recipes have to be stored in [schema.org/Recipe](https://schema.org/Recipe/) format.
This is a command line program.

Not intended for crawling a large amount of recipes. 

The websites that it crawls is configured via a YAML file, see [website_sources.yaml](website_sources.yaml).
Most of the options are to be implemented in later version.

The cookbooks are output into a single JSON file that is named `cookbook.json`. If that file name already exists it will name it `cookbook-1.json` and so on.

Information about the design and future improvements is [recipe-crawler.py](in the source).
 This still needs some fine tuning to improve the algorithm so that it will more quickly get the recipes and put the license inforamtion into the file.

The code tool used for formatting is [black](https://black.readthedocs.io/).

##  Requirements
Python 3.6 or greater

These python libraries have to be installed before the crawler can be used.

This has several [requirements](requirements.txt).  
Requirements these can be installed on the command line with
```
> pip install -r requirements.txt
```

OR Install the python libraries individually if prefered:
* [beautifulsoup4](https://beautiful-soup-4.readthedocs.io/)
* [loguru](https://loguru.readthedocs.io/)
* [requests](https://docs.python-requests.org/)
* [scrape-schema-recipe](https://github.com/micahcochran/scrape-schema-recipe)
* [PyYAML](https://pyyaml.org/)


## License
Licensed under the Apache License, Version 2.0

See the [LICENCE](LICENCE) file for terms.