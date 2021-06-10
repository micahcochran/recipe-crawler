## recipe-crawler.py
This command line interface (CLI) web crawler that creates a cookbook from recipes found on websites.  
The website recipes have to be stored in [schema.org/Recipe](https://schema.org/Recipe/) format.

Not intended for crawling a large amount of recipes. 

The websites that it crawls is configured via a YAML file, see [website_sources.yaml](website_sources.yaml).
Most of the options are to be implemented in a later version.

The cookbooks are output into a single JSON file that is named `cookbook.json`. If that file name already exists it will name it `cookbook-1.json` and so on.

Information about the design and future improvements is [recipe-crawler.py](in the source).
This still needs some fine tuning to improve the algorithm so that it will more quickly get the recipes and put the license information into the file.

The code tool used for formatting is [black](https://black.readthedocs.io/).

## Running
This has to be run from the command line.  `websites_config.yaml` is a configuration file for specifying the websites to be crawled.

### Linux/Mac
```bash
/some/folder/recipe-crawler$ ./recipe_crawler.py (websites_config.yaml)
```

### Windows
```
C:\some\folder\recipe-crawler> python recipe_crawler.py (websites_config.yaml)
```

##  Requirements
Python 3.6 or greater

These python libraries have to be installed before the crawler can be used.

This has several [requirements](requirements.txt).  
Requirements these can be installed on the command line with
```
> pip install -r requirements.txt
```

OR Install the python libraries individually if preferred:
* [Beautiful Soup](https://beautiful-soup-4.readthedocs.io/)
* [loguru](https://loguru.readthedocs.io/)
* [Pendulum](https://pendulum.eustace.io/)
* [PyYAML](https://pyyaml.org/)
* [requests](https://docs.python-requests.org/)
* [scrape-schema-recipe](https://github.com/micahcochran/scrape-schema-recipe)


## License
Licensed under the Apache License, Version 2.0

See the [LICENCE](LICENCE) file for terms.

## Performance by version

| Version | Number of Recipes | Minutes:Seconds 🠗 | # Webpages DLed | Derived ----> | webpages DLed/recipe 🠗 | seconds/recipe 🠗 | 
| :-- | :-: | :-: | :-: | | :-: | :-: |
| 0.1.0 | 20 | 1:16 | 39 | | 2 | 3.8 |
| 0.0.2 | 20 | 4:00 | 79 | | 4 | 12 |
| 0.0.1 | 20 | 7:20 | 122 | | 6 | 22 |

🠗 symbol indicates that for the statistic being lower is better