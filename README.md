## recipe-crawler.py
This command line interface (CLI) web crawler that creates a cookbook from recipes found on websites.  
The website recipes have to be stored in [schema.org/Recipe](https://schema.org/Recipe/) format.

This is not designed to crawling a large amount of recipes. 

The websites that it crawls is configured via a YAML file, see [website_sources.yaml](website_sources.yaml).
Most of the options are to be implemented in a later version.

By default, cookbooks are output into a single JSON file that is named `cookbook.json`. If that file name already exists it will name it `cookbook-1.json` and so on.

`taste.py` can perform simple queries on the `cookbook.json` on the command line.  This includes querying the names of the attributes, the attributes, length, and viewing a recipe at a particular index number.

Information about the design and future improvements is [recipe-crawler.py](in the source).

The code tool used for formatting is [black](https://black.readthedocs.io/).

## Running
This has to be run from the command line.  `websites_config.yaml` is a configuration file for specifying the websites to be crawled.

### Linux/Mac
From the command line run:
```bash
/some/folder/recipe-crawler$ ./recipe_crawler.py --config websites_config.yaml
```

### Windows
From the command line run:
```
C:\some\folder\recipe-crawler> python recipe_crawler.py --config websites_config.yaml
```

Note: the Linux/Mac command line will be used in examples, but you should be trivial to adapt the example to Windows. Note some systems may need to use `python3` instead.

### Command Line Options

**The command line options were changed in version 0.3.0.**

```bash
$ ./recipe_crawler.py --help
usage: recipe_crawler.py [-h] [-c CONFIG] [-f FILTER] [--limit LIMIT]
                         [-o OUTPUT] [--version]

Recipe Crawler to that saves a cookbook to a JSON file.

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        website configuration YAML file
  -f FILTER, --filter FILTER
                        filter names of websites to crawl
  --limit LIMIT         Limit of number of recipes to collect (default: 20)
  -o OUTPUT, --output OUTPUT
                        Output to a JSON file
  --version             show program's version number and exit
```

As an example, to crawl only the bevvy.co website and output the cookbook to the `bevvy-co.json` file:
```bash
$ ./recipe_crawler.py --config website_source-open_source.yaml --filter bevvy --limit 5 --output bevvy-co.json
```

If you just run `./recipe_scraper.py`, it will use the defaults for crawling.

Also a license file `license-bevvy-co.md` is generated, which documents that licensing for the cookbooks.  In 2021, these usually have to to be specified in the YAML config file using `license` option with a URL about the licensing of that information.

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
* [recipe-scrapers](https://github.com/hhursev/recipe-scrapers)
* [scrape-schema-recipe](https://github.com/micahcochran/scrape-schema-recipe)


For development, install the dependent libaries typing:
```
> pip install -r requirements-dev.txt
```
### Optional Dependency
If you want to download pages using [Brotli compression](https://en.wikipedia.org/wiki/Brotli)
* ensure requests >= 2.26.0 is installed, in order to check your request version (two ways)
  * `$ python -c "import requests;print(requests.__version__)"`
  * `$ pip list | grep requests`
* AND install either [_brotli_](https://github.com/google/brotli) or [_brolicffi_](https://pypi.org/project/brotlicffi/), via `$ pip install brotli` or `$ pip install brotlicffi`.

Most web servers support gzip compression and have for a long time.  Brotli typically yields a little higher compression than gzip. Since about 2016, the support for this compression algorithm has taken off.  Not all web servers support this compression method.

keycdn has a [Brotli Test Tool](https://tools.keycdn.com/brotli-test) that tests for a web server's supports of Brotli compression.  Perhaps check the websites that you wish to crawl.

Note: Some systems may need to use `python3` instead of `python` and `pip3` instead of `pip`.  This is a legacy from Python 2.x being still installed on some systems.

## License
Licensed under the Apache License, Version 2.0

See the [LICENCE](LICENCE) file for terms.

## Performance by version

| Version | Number of Recipes | Minutes:Seconds 🠗 | # Webpages DLed | Derived ----> | webpages DLed/recipe 🠗 | seconds/recipe 🠗 | 
| :------ | :---------------: | :---------------: | :-------------: | ------------- | :--------------------: | :-------------: |
| 0.3.0 | 20 | 1:31 | 45 | |  2.3 | 4.6 |
| 0.2.1 | 20 | 1:55 | 61 | | 3 | 5.8 |
| 0.2.0-pre | 20 | 1:28 | 51* | | 2.6 | 4.4 |
| 0.1.0 | 20 | 1:16 | 39 | | 2 | 3.8 |
| 0.0.2 | 20 | 4:00 | 79 | | 4 | 12 |
| 0.0.1 | 20 | 7:20 | 122 | | 6 | 22 |

🠗 symbol indicates that for the statistic being lower is better
\* first version to detect duplicate recipes

## Derived Projects
This project was used to create [json-cookbook](https://github.com/micahcochran/json-cookbook).  These are recipes that can easily be used in for testing software that uses recipes.  The recipes are licensed under Creative Commons or public domain.