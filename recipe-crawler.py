#!/usr/bin/env python3

###  WHAT  ###############################################################
# This is a web crawler to for a few recipe websites to compile a cookbook in JSON format.
# This is intented to run pretty quickly (a few minutes), not be long lived process.
# Hopefully, it won't behave badly.  Logging will tell about its behavior.
#
# The design is simple and slow. (It is slow, it takes about 7 minutes to find 20 recipes.)

###  PURPOSE  ############################################################
#
# The purpose of this code is to crawl web site, copy recipes, and create a cookbook that can be
# distributed because it is made up of recipes that have licenses that are open or public domain.

###  RELEASE  ############################################################
#
# 0.0.1 Released 2021-06-03
#       Works, but still has most of the debugging enabled.
#

###  DESIGN - CLASSES ####################################################
#
# MultiCrawler - this is a class that directs multiple instances of Crawler class.
#
# Crawler - handles one website.  It crawls the website, parses the schema.org/Recipe results,
# and finds another page on the website to visit next.
#
# LogUponChanged - this is intened to print a log message when the variable's value has changed.
#
# URLTest - contains tests that are performed on URLs
#

# === Possible Improvements ==============================================
#
# * Add Runtime.
#
# * Add counter on the number of request.get calls made.
#
# * Need to have a modify the strategy for picking the next url to visit.  It needs to prioritize ones that will lead to a recipe.
#   (url might look like https://www.example.com/recipes/pizza) Add those URLs to the queue first.
#   Then, fall back on picking a random URL stategy.   (for version 0.1.0)
#
# * Should add a license key to the schema.org/Recipe for the Open recipes.  This should be in form of a URL
#   that is taken from the configuration file.  (for version 0.1.0)
#
#  * Sitemap support could be added.  It might help some of the crawlers that exhaust all the links.
#
#  * I'd slightly like to have a cralwer for NIH Healthy Eating website, which has public domain recipes.
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

# ----- Python native imports -----
import copy
from collections import deque
from itertools import cycle
import json
import logging
from random import randint
import os.path
import sys
from time import sleep

# use this typing syntax, Python 3.9 allows builtins (dict, list) to used
from typing import Dict, List
import urllib.robotparser
import urllib.parse

# ----- external imports -----
from bs4 import BeautifulSoup
from loguru import logger

# import recipe_scrapers
import requests
import scrape_schema_recipe
import yaml

# Flag slows down the execution of the program so that it is enough time to be able to react if it
# isn't performing correctly.
SLOW_DEBUG = True

# This is the user-agent
__VERSION__ = "0.0.1"
USER_AGENT = f"crawl-recipes.py/{__VERSION__}"
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
    The class manges multiple crawlers.  It will sequantially run these crawlers on different website
    until those crawlers have collectively  met/exceeded the recipe_limit number of recipes.
    """

    def __init__(self, recipe_limit: int = 100) -> None:
        self.recipe_limit: int = recipe_limit
        self.num_recipes: int = 0
        self.crawlers: List = []
        self.crawler_iter = None
        # This is for crawlers that get removed.
        self.inactive_crawler: List = []

    def add_crawler(self, url):
        self.crawlers.append(Crawler(url))

        # create an iterator that will cycle through the crawlers
        self.crawler_iter = cycle(self.crawlers)

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


##### class Crawler ######################################################
# Provide a url and it will crawl the website scraping Schema.org/Recipe patterns.  It also finds another page to crawl.
class Crawler:
    """This crawls for one website."""

    def __init__(self, url):
        self._url_queue = deque()
        self.base_url = url
        self._url_queue.append(url)

        # This is a list of anchors found on the site that will be randomly pulled from.
        self._anchor_list = []
        # this is a list of dictionaries
        self.recipe_json: List = []
        # stores the HTML content
        self.html_pages: List = []
        # list of urls already visted, so as to not visit again
        self.been_there_urls: List = []

        robots_txt_url = urllib.parse.urljoin(url, "robots.txt")
        self.robotparse = urllib.robotparser.RobotFileParser(robots_txt_url)
        self.robotparse.read()
        logger.debug(f"Reading robots.txt at: {robots_txt_url}")

    def crawl(self) -> int:
        """This crawls a single page.
        returns the number of recipes found"""
        num_recipes = 0

        response = self._download_page()
        scrapings = self._scrape_page(response.text)

        if scrapings is not None:
            if isinstance(scrapings, dict):
                num_recipes += 1
                self.recipe_json.append(scrapings)
            else:  # for lists
                num_recipes += len(scrapings)
                self.recipe_json.extend(scrapings)
            self.html_pages.append(response.text)
            logging.debug("Found a recipe!!!")

        self._find_random_url(response.text)

        return num_recipes

    def _download_page(self):
        """
        returns a requests response object
        """
        url = self._url_queue.popleft()
        self.been_there_urls.append(url)
        logger.debug(f"Visiting {url}")

        return requests.get(url, headers=REQUESTS_HEADERS)

    def _scrape_page(self, html):
        """
        return dict or List, if it is empty it will be None
        """
        recipe = scrape_schema_recipe.loads(html)
        if len(recipe) > 0:
            if len(recipe) == 1:
                return recipe[0]
            else:
                return recipe

        return None

    def _find_random_url(self, html):
        """finds a random url within the provided html,
        store all of urls in anchors in a page in a list, randomly selects url to visit from that list,
        makes sure that the url is valid and able to be visited."""
        # get all the anchor tags
        soup = BeautifulSoup(html, "html.parser")
        all_anchors = soup.find_all("a")

        href_val_for_anchors = [a.get("href") for a in all_anchors]
        # add all the href urls from the anchor tags to a list
        # example a tag<a href="http://example.com/">Link Text</a>
        self._anchor_list.extend(href_val_for_anchors)

        # NOTE: This could be stored longer.
        urltest = URLTest(self.base_url)

        flag_no_valid_url = False

        # Loops until it find a valid URL to visit next
        while flag_no_valid_url is False:
            if len(self._anchor_list) == 0:
                raise ValueError("Anchor List is empty.")

            i = randint(0, len(self._anchor_list) - 1)
            logger.debug(f"Random number is: {i}")
            # get a random anchor, remove it from the anchor list
            rand_anchor = self._anchor_list.pop(i)

            # must be a string
            if not isinstance(rand_anchor, str):
                continue

            # skip these href's because those won't lead to a webpage link
            if rand_anchor.startswith(("#", "javascript:", "mailto:")):
                continue

            if urltest.is_absolute_url(rand_anchor):
                # is the URL on the same domain?
                if not urltest.is_same_domain(rand_anchor):
                    continue
            else:
                # convert relative URL into an absolute URL
                rand_anchor = urllib.parse.urljoin(self.base_url, rand_anchor)

            # Has the crawler already been to (visited) this URL?
            if rand_anchor in self.been_there_urls:
                continue

            # Check if robots.txt rules allow going to this URL
            if self.robotparse.can_fetch(USER_AGENT, rand_anchor) is False:
                continue

            # add url to the queue
            self._url_queue.append(rand_anchor)
            flag_no_valid_url = True

            logger.debug(f"Next URL to crawl is {rand_anchor}")
            if SLOW_DEBUG is True:
                # sleeps 1 second to allow for the programmer to watch it for messing up.
                sleep(1)


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

    def __init__(self, baseurl: str):
        """baseurl is the start URL of the website"""
        self.baseurl = baseurl
        self.basesplit = urllib.parse.urlsplit(self.baseurl)

    def is_absolute_url(self, url: str) -> bool:
        """Simplistic test if this is a URL
        returns True if it is an absolute URL, False if not"""

        return url.startswith("http://") or url.startswith("https://")

    def is_same_domain(self, url: str) -> bool:
        """Tests if url is in the same domain as the base_url"""
        urlspl = urllib.parse.urlsplit(url)

        return self.basesplit.netloc == urlspl.netloc


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

    #   NOTE: Get 20 recipes for testing.
    mc = MultiCrawler(20)
    for source in website_sources_list:
        # logger.debug('KEYS: {}'.format(source['site'].keys()))

        logger.debug(f"Adding crawler for: {source['site']['url']}")
        mc.add_crawler(source["site"]["url"])

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

    logger.debug(f"Wrote '{filename}'.")
