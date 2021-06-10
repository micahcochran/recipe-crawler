#!/usr/bin/env python3

#
# Copyright 2021  Micah Cochran
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


###  WHAT  ###############################################################
# This is a web crawler to for a few recipe websites to compile a cookbook in JSON format.
# This is intended to run fairly quickly (a few minutes), not be a long lived process.
#
# The design is intended to be simple.

###  PURPOSE  ############################################################
#
# The purpose of this code is to crawl web site, copy recipes, and create a cookbook.
# That cookbook can be used to test recipe software.  If open source/public domain recipes
# are used, that cookbook could be distributed.

###  RELEASE  ############################################################
#
# 0.1.0  Release 2021-06-09
#        Note: This release accomplishes many of my goals.
#        * functionality of Crawler._find_random_url has been split between _rank_url() and
#          _mine_url(), which work together.
#        * Crawler._rank_url() ranks the URLs based on the recipe_url defined in the yaml config.
#          URLs that match recipe_url get put in a higher priority list.
#        * _mine_url processes all of the anchors of a webpage into lists.
#        * Crawler._download_page now picks web pages to download from.
#        * Add timeout value to requests.get()
#        * Replaced deque (double ended queue) with Python list.  Python lists are common and the double
#           ended queue provided no advantages.

# 0.0.2  Release 2021-06-06
#        * Logs runtime and number of web page requests.
#        * Add Pendulum library to print out an English runtime message.
#        * Correct spelling errors.
#        * Rename __VERSION__ to __version__
#        * Add url and license to the schema output.
#        * Add unit testing for URLTest Class.
#        * Fixed bug in URLTest.is_same_domain(), the same domain names with different letter
#          cases were returning false. Now, WWW.EXAMPLE.COM and www.example.com, will return
#          True for the is_same_domain() function.
#
# 0.0.1  Released 2021-06-05
#        Works, but still has most of the debugging enabled.
#

###  DESIGN - CLASSES ####################################################
#
# MultiCrawler - this is a class that directs multiple instances of Crawler class.
#
# Crawler - handles one website.  It crawls the website, parses the schema.org/Recipe results,
# and finds another page on the website to visit next.
#
# LogUponChanged - this is intended to print a log message when the variable's value has changed.
#
# URLTest - contains tests that are performed on URLs
#

# === Possible Improvements ==============================================
#
#
#
#
#  * I'd slightly like to have a crawler for NIH Healthy Eating website, which has public domain recipes.
#    There are a few problems with that idea.
#    (1) recipe_scrapers library would need to be used because the website does not format recipes
#        in schema.org/Recipe format.  Crawler was not really designed to be extended in that manner.
#        Note: I could fork the portions of the recipe_scrapers "nihhealthyeating.py" that I want using BeautifulSoup.
#              Is it worth the trouble?  It would probably add about 30 lines of code.
#    (2) recipe_scrapers library needs to have a public function that allows you to supply a url
#        and the text of the webpage.  recipe_scraper must have a URL, that will cause another
#        webpage to be downloaded.  There was already an issue (#170) raised about using the library with
#        a scraping platform, so there may some day be a public interface support.  I explained how this
#        could be addressed in the issue.
#    (3) recipe_scrapers would have to be wrapped in schema.org/Recipe JSON-LD.  This isn't difficult.  Perhaps a
#        feature that recipe_scrapers might even take a Pull-Request for the code.
#
#        recipe_scraper issue #170:  https://github.com/hhursev/recipe-scrapers/issues/170
#
#  * Implement saving HTML files with recipes to a folder.
#
#  * Sitemap support. This might help some of the crawlers that exhaust all their links.
#    (Version 0.2.0)
#
#  * Some websites almost instantly exit out.  I'm not to sure why, but I'm sure other web crawlers have encountered this.
#    Some of it may be due to using non-standard forms for URLs.  Prehaps adding a sitemap mode might be a way to work around this.
#
#  * Might be nice to for it to generate some kind of license report (Markdown) file of the cookbook's recipes.

# ----- Python native imports -----
import copy
from itertools import cycle
import json
import logging
from random import randint
import os.path
import sys
from time import sleep

# Use this typing syntax.
# Python 3.9 allows builtins (dict, list) to be used
# In Python 3.7 and 3.8, can `from __future__ import annotations`
from typing import Dict, List, Tuple
import urllib.robotparser
import urllib.parse

# ----- external imports -----
from bs4 import BeautifulSoup
from loguru import logger
import pendulum

# import recipe_scrapers
import requests
import scrape_schema_recipe
import yaml

# Flag slows down the execution of the program so that it is enough time to be able to react if it
# isn't performing correctly.
SLOW_DEBUG = True

__version__ = "0.1.0"
# This is the user-agent
USER_AGENT = f"recipe_crawler.py/{__version__}"
REQUESTS_HEADERS = {"user-agent": USER_AGENT}

# This is unused
FAKE_REQUESTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/88.0"
}

######  class LogUponChanged  ############################################
# This class will print a message when the variable has changed
# NOTE: This is a very simple class.
class LogUponChanged:
    def __init__(self, var, fmesg="Variable changed {}") -> None:
        self.var = copy.deepcopy(var)
        self.fmesg = fmesg

    def check(self, var) -> None:
        if var != self.var:
            self.var = copy.deepcopy(var)
            logging.debug(self.fmesg.format(var))


######  class MultiCrawler  ##############################################
class MultiCrawler:
    """
    The class manges multiple crawlers.  It will sequentially run these crawlers on different website
    until those crawlers have collectively  met/exceeded the recipe_limit number of recipes.
    """

    def __init__(self, recipe_limit: int = 100) -> None:
        self.recipe_limit: int = recipe_limit
        self.num_recipes: int = 0
        self.crawlers: List = []

        # This is for crawlers that get removed.
        self.inactive_crawler: List = []

    def add_crawler(self, url: str, recipe_url: str = "", license=None):
        self.crawlers.append(Crawler(url, recipe_url, license))

        # create an iterator that will cycle through the crawlers
        self.crawler_iter: cycle[Crawler] = cycle(self.crawlers)

    def remove_crawler(self, base_url) -> bool:
        for i in range(len(self.crawlers)):
            if self.crawlers[i].base_url == base_url:
                c = self.crawlers.pop(i)
                self.inactive_crawler.append(c)
                self.crawler_iter = cycle(self.crawlers)
                return True

        return False

    def run(self):
        """run crawlers sequentially until enough recipes are collected"""
        log_change = LogUponChanged(self.num_recipes)
        # loop until the recipe limit is reached or there are no more crawlers left
        while self.num_recipes < self.recipe_limit or len(self.crawlers) < 1:
            crawler = next(self.crawler_iter)
            try:
                self.num_recipes += crawler.crawl()
            except ValueError:
                logger.info(f"Terminating crawler for {crawler.base_url}")
                if self.remove_crawler(crawler.base_url) is False:
                    raise RuntimeError("Fatal error removing crawler.")
            # log message when the number of recipes collected changes
            log_change.check(self.num_recipes)
            if SLOW_DEBUG is True:
                logger.debug(f"self.num_recipes = {self.num_recipes}")
                # Sleeps for 1 second, allow for the user to watch for the crawler messing up.
                # In effect also "throttling" out how much bandwidth is being used.
                sleep(1)

    def results_dict(self) -> List[Dict]:
        """resulting singular list of dictionaries that represent schema-recipes"""
        ret = []

        for c in self.crawlers:
            ret.extend(c.recipe_json)

        return ret

    def results_html(self) -> List[Dict]:
        """resulting singular list of dictionaries that represent schema-recipes"""
        ret = []

        for c in self.crawlers:
            ret.extend(c.html_pages)

        return ret

    def results_num_get_calls(self) -> int:
        return sum([c.num_get_calls for c in self.crawlers])


##### class Crawler ######################################################
# Provide a url and it will crawl the website scraping Schema.org/Recipe patterns.  It also finds another page to crawl.
class Crawler:
    """This crawls for one website."""

    def __init__(self, url: str, recipe_url: str = "", license=None):
        self.base_url = url

        # list of urls that have a better change to have recipes
        self._url_list_high: List = [url]
        # This is a list of anchors found on the site that will be randomly pulled from to continue crawling.
        self._url_list_low: List = []

        # this is a list of dictionaries
        self.recipe_json: List = []
        # stores the HTML content
        self.html_pages: List = []
        # list of urls already visited, so as to not visit again
        self.been_there_urls: List = []
        # store the number of requests.get() calls made
        self.num_get_calls = 0

        # url stem that should have recipes
        # something like:  http://www.example.com/recipes/
        self._recipe_url = recipe_url
        if recipe_url is None:
            self._recipe_url = ""

        self._license = None
        if license and license.lower() != "proprietary":
            if URLTest().is_absolute_url(license):
                self._license = license

        robots_txt_url = urllib.parse.urljoin(url, "robots.txt")
        self.robotparse = urllib.robotparser.RobotFileParser(robots_txt_url)
        self.robotparse.read()
        logger.debug(f"Reading robots.txt at: {robots_txt_url}")

        self.urltest = URLTest(url)

    def crawl(self) -> int:
        """This crawls a single page.
        returns the number of recipes found"""
        num_recipes = 0

        response = self._download_page()
        scrapings = self._scrape_page(response)
        self._mine_anchors(response)

        if scrapings is not None:
            if isinstance(scrapings, dict):
                num_recipes += 1
                self.recipe_json.append(scrapings)
            else:  # for lists
                num_recipes += len(scrapings)
                self.recipe_json.extend(scrapings)
            self.html_pages.append(response.text)
            logging.debug("Found a recipe!!!")

        # self._find_random_url(response.text)

        return num_recipes

    def _download_page(self):
        """
        Get an url from the list and download a webpage

        returns a requests.Response object
        """
        # this picks a url
        if len(self._url_list_high) > 0:
            # pops the like a dequeue
            url = self._url_list_high.pop(0)
        elif len(self._url_list_low) > 0:
            # randomly get an item off the low list
            r = randint(0, len(self._url_list_low))
            url = self._url_list_low.pop(r)
        else:
            raise ValueError("The anchor lists are empty.")

        self.been_there_urls.append(url)
        logger.debug(f"Visiting {url}")

        self.num_get_calls += 1
        return requests.get(url, headers=REQUESTS_HEADERS, timeout=5)

    def _scrape_page(self, response: requests.Response):
        """
        scrapes a page
        input: response is a requests.Response object from requests.get()

        return dict or List, if it is empty it will be None
        """
        recipe = scrape_schema_recipe.loads(response.text)
        if len(recipe) > 0:
            if len(recipe) == 1:
                # if the schema output doesn't already have the url/license, add those to the output

                if recipe[0].get("url") is None:
                    recipe[0]["url"] = response.url

                if self._license is not None and recipe[0].get("license") is None:
                    recipe[0]["license"] = self._license
                return recipe[0]
            else:
                return recipe

        return None

    def _mine_anchors(self, response: requests.Response):
        """Mines anchors from the webpage response.

        This takes all of the anchors and evaluates them and places them into the proper lists."""
        # get all the anchor tags
        soup = BeautifulSoup(response.text, "html.parser")
        all_anchors = soup.find_all("a")
        for a in all_anchors:
            href = a.get("href")
            score, url = self._rank_url(href)

            if score == 1:  # High score
                self._url_list_high.append(url)
            elif score == 0:  # Low score
                self._url_list_low.append(url)

            # otherwise skip the URL, especially the ones with a -1 score

    def _rank_url(self, url: str) -> Tuple[int, str]:
        """Rank the url's likelihood of having recipe data.
        parameter: url

        returns tuple (score, absolute_url)
            score as an integer
                 1  - likely to have a recipe
                 0  - unlikely to have a recipe
                -1  - do not visit
                    (There are numerous reasons to disquality a URL).
        """

        # must be a string
        if not isinstance(url, str):
            return (-1, url)

        # these hrefs won't lead to a webpage link
        if url.startswith(("#", "javascript:", "mailto:")):
            return (-1, url)

        if self.urltest.is_absolute_url(url):
            # is the URL on the same domain?
            if not self.urltest.is_same_domain(url):
                return (-1, url)
        else:
            # convert relative URL into an absolute URL
            url = urllib.parse.urljoin(self.base_url, url)

        # Has the crawler already been to (visited) this URL?
        if url in self.been_there_urls:
            return (-1, url)

        # Check if robots.txt rules allow going to this URL
        if self.robotparse.can_fetch(USER_AGENT, url) is False:
            return (-1, url)

        # check if there is some way to do this.
        if self._recipe_url != "" and url.startswith(self._recipe_url):
            return (1, url)

        return (0, url)


#  See "Possible Improvements" section
#  Need some way to do an end-run around scrape_me()'s request.get function.
#  class NIHHealthyEatingCrawler(Crawler):
#    def _scrape_page(self, html):
#        recipe_scrapers.scrape_me(html)


# TODO: most of the configuration data isn't currently used.
def load_website_sources_list(
    config_filename: str = "website_sources.yaml",
) -> List[Dict]:
    """
    Loads a list of websites with attributes about those websites as a List of Dicts.
    """
    # loads the websites to scrape from
    with open(config_filename, "r") as fp:
        return [data for data in yaml.safe_load_all(fp)]


class URLTest:
    """Class of tests for URLs"""

    def __init__(self, baseurl: str = None):
        """baseurl is the start URL of the website"""
        self.baseurl = baseurl
        self.basesplit = None

        if baseurl:
            self.basesplit = urllib.parse.urlsplit(baseurl)

    def is_absolute_url(self, url: str) -> bool:
        """Simplistic test if this is a URL
        returns True if it is an absolute URL, False if not"""

        return url.startswith(("http://", "https://"))

    def is_same_domain(self, url: str) -> bool:
        """Tests if url is in the same domain as the base_url"""
        if self.basesplit is None:
            raise ValueError("self.basesplit is None, cannot run is_same_domain()")

        urlspl = urllib.parse.urlsplit(url)

        return self.basesplit.netloc.lower() == urlspl.netloc.lower()


##########  MAIN  #########################################################
if __name__ == "__main__":
    website_sources_list = []

    # if there is one argument use that file name for the configuration
    if len(sys.argv) == 2:
        # does this file exist?
        if not os.path.exists(sys.argv[1]):
            logger.error("File '{}' does not exist. Exiting.", sys.argv[1])
            sys.exit(1)
        website_sources_list = load_website_sources_list(sys.argv[1])
    else:
        # use default name for configuration
        website_sources_list = load_website_sources_list()

    start_time = pendulum.now()
    #   NOTE: Get 20 recipes for testing.
    mc = MultiCrawler(20)
    for source in website_sources_list:
        # logger.debug('KEYS: {}'.format(source['site'].keys()))

        logger.debug(f"Adding crawler for: {source['site']['url']}")
        mc.add_crawler(
            source["site"]["url"],
            source["site"].get("recipe_url"),
            source["site"].get("license"),
        )

    mc.run()

    recipes_dict = mc.results_dict()

    # create unique cookbook filename
    filename = "cookbook.json"
    i = 0
    while os.path.exists(filename):
        i += 1
        filename = f"cookbook-{i}.json"
    # save to file

    with open(filename, "w") as fp:
        json.dump(recipes_dict, fp)

    logger.info(f"Wrote file '{filename}'.")

    logger.info(f"Number of web pages downloaded: {mc.results_num_get_calls()}")
    runtime_str = pendulum.now().diff(start_time).in_words()
    logger.info(f"Program's Runtime: {runtime_str}")
