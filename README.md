## recipe-crawler.py
This command line interface (CLI) web crawler that creates a cookbook from recipes found on websites.  
The website recipes have to be stored in [schema.org/Recipe](https://schema.org/Recipe/) format.

Not intended for crawling a large amount of recipes. 

The websites that it crawls is configured via a YAML file, see [website_sources.yaml](website_sources.yaml).
Most of the options are to be implemented in a later version.

The cookbooks are output into a single JSON file that is named `cookbook.json`. If that file name already exists it will name it `cookbook-1.json` and so on.

`taste.py` can perform simple queries on the `cookbook.json` on the command line.  This includes querying the names of the attributes, the attributes, length, and viewing a recipe at a particular index number.

Information about the design and future improvements is [recipe-crawler.py](in the source).
This still needs some fine tuning to improve the algorithm so that it will more quickly get the recipes and put the license information into the file.

The code tool used for formatting is [black](https://black.readthedocs.io/).

## Running
This has to be run from the command line.  `websites_config.yaml` is a configuration file for specifying the websites to be crawled.

### Linux/Mac
From the command line run:
```bash
/some/folder/recipe-crawler$ ./recipe_crawler.py (websites_config.yaml)
```

### Windows
From the command line run:
```
C:\some\folder\recipe-crawler> python recipe_crawler.py (websites_config.yaml)
```

##  Requirements
Python 3.6 or greater

These python libraries have to be installed before the crawler can be used.

The software has several [requirements](requirements.txt).  
Requirements these can be installed on the command line with
```
> pip install -r requirements.txt
```

OR Install the python libraries individually:
* [Beautiful Soup](https://beautiful-soup-4.readthedocs.io/)
* [loguru](https://loguru.readthedocs.io/)
* [Pendulum](https://pendulum.eustace.io/)
* [PyYAML](https://pyyaml.org/)
* [requests](https://docs.python-requests.org/)
* [reppy](https://github.com/seomoz/reppy)
* [recipe-scrapers](https://github.com/hhursev/recipe-scrapers)
* [scrape-schema-recipe](https://github.com/micahcochran/scrape-schema-recipe)


## License
Licensed under the Apache License, Version 2.0

See the [LICENCE](LICENCE) file for terms.

## Performance by version

| Version | Number of Recipes | Minutes:Seconds 🠗 | # Webpages DLed | Derived ----> | webpages DLed/recipe 🠗 | seconds/recipe 🠗 | 
| :------ | :---------------: | :---------------: | :-------------: | ------------- | :--------------------: | :-------------: |
| 0.2.1 | 20 | 1:55 | 61 | | 3 | 5.8 |
| 0.2.0-pre | 20 | 1:28 | 51* | | 2.6 | 4.4 |
| 0.1.0 | 20 | 1:16 | 39 | | 2 | 3.8 |
| 0.0.2 | 20 | 4:00 | 79 | | 4 | 12 |
| 0.0.1 | 20 | 7:20 | 122 | | 6 | 22 |

🠗 symbol indicates that for the statistic being lower is better
\* first version to detect duplicate recipes

## Derived Projects
This project was used to create [json-cookbook](https://github.com/micahcochran/json-cookbook).  These are recipes that can easily be used in for testing software that uses recipes.  The recipes are licensed under Creative Commons or public domain.