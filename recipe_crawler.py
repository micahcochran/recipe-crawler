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

###  DESIGN - CLASSES ####################################################
#
# MultiCrawler - this is a class that directs multiple instances of Crawler class.
#
# Crawler - handles one website.  It crawls the website, parses the schema.org/Recipe results,
#           and finds another page on the website to visit next.
#
# RecipeScrapersCrawler - Derived from Crawler. Uses recipe_scraper library for a few websites do not
#                         conform to schema.org/Recipe format.
#
# URLTest - contains tests that are performed on URLs
#

# === Possible Improvements ==============================================
#
#  * Implement saving HTML files with recipes to a folder.
#
#  * Sitemap support. This might help some of the crawlers that exhaust all their links.
#
#  * Some websites almost instantly exit out.  I'm not too sure why, but I'm sure other web crawlers have encountered this.
#    Some of it may be due to using non-standard forms for URLs.  Prehaps adding a sitemap mode might be a way to work around this.
#
#  * There could be more logic to detecting if recipes are the same by the URL, but this would require some pattern matching code in the URL.
#    Logging the matching recipes would aid in figuring that out.
#
#  * Perhaps implement some way of storing the images?  Could implement do some kind of caching system.  URL hash key scheme
#     This could be stored as a json file of URLS to a folder of images.
#     Feed the URL into a hash algorithm, like md5 (in hashlib),  (hexdigest() to output hexadecimal) then store the images as a filename.
#     The images could be stored as blobs in a SQLite database.
#
#     Need to make it easy to interface this for external projects.
#
#     This behavior somehow needs to be optional.  (command line interface: --fetch-images)
#
#  * Fix bug: recipes are being downloaded with the same URLs as ones previously downloaded.
#
#  * Improve command line options and make them more POSIX-like.
#
#  * Number of bytes downloaded is not accurate due to not being able to always get the "Content-Length" header.
#
#  * Could make the recipe-scrapers library an optional add-on.  It is currently only used for two websites.  
#    Probably should move it to its own file that only gets imported when needed.

# ----- Python native imports -----
import argparse
from datetime import datetime, timedelta
from io import StringIO
from itertools import cycle
import json
from random import randint
import os.path
import sys
from time import sleep
import urllib.parse

# Use this typing syntax.
# Python 3.9 allows builtins (dict, list) to be used
# In Python 3.7 and 3.8, use `from __future__ import annotations`
from typing import Dict, List, Tuple, Union


# ----- external imports -----
from bs4 import BeautifulSoup
import isodate
from loguru import logger
import pendulum
import recipe_scrapers
from recipe_scrapers.settings import settings as recipe_scrapers_settings
from recipe_scrapers._exceptions import ElementNotFoundInHtml
import reppy
import requests
import scrape_schema_recipe
import yaml

# Flag slows down the execution of the program so that it is enough time to be able to react if it
# isn't performing correctly, when set to True.  False turns this off.
SLOW_DEBUG = True

__version__ = "0.3.0"
# This is the user-agent
USER_AGENT_ROBOTS = "RecipeCrawlerPY"
USER_AGENT = f"RecipeCrawlerPY/{__version__}"
REQUESTS_HEADERS = {"user-agent": USER_AGENT}


# put it in test mode for RecipeScrapersCrawler
if recipe_scrapers_settings.TEST_MODE is not False:
    raise RuntimeError("TEST_MODE should be False.")
recipe_scrapers_settings.TEST_MODE = True


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

    def add_crawler(
        self,
        url: str,
        recipe_url: str = "",
        license=None,
        start_url: str = "",
        site_title: str = "",
    ) -> None:
        if "myplate.gov" in url or "healthyeating.nhlbi.nih.gov" in url:
            self.crawlers.append(
                RecipeScrapersCrawler(url, recipe_url, license, start_url, site_title)
            )
        else:
            self.crawlers.append(
                Crawler(url, recipe_url, license, start_url, site_title)
            )

        # create an iterator that will cycle through the crawlers
        self.crawler_iter: cycle[Crawler] = cycle(self.crawlers)

    def remove_crawler(self, base_url) -> bool:
        for i in range(len(self.crawlers)):
            if self.crawlers[i].base_url == base_url:
                c = self.crawlers.pop(i)
                self.inactive_crawler.append(c)
                # TODO len(self.crawlers) == 0
                self.crawler_iter = cycle(self.crawlers)
                return True

        return False

    def run(self) -> None:
        """run crawlers sequentially until enough recipes are collected"""
        # loop until the recipe limit is reached or there are no more crawlers left
        while self.num_recipes < self.recipe_limit or len(self.crawlers) < 1:
            crawler = next(self.crawler_iter)
            try:
                self.num_recipes += crawler.crawl()
            except AnchorListsEmptyError as e:
                logger.info(f"E is: {e}")
                logger.info(f"Terminating crawler for {crawler.base_url}")
                if self.remove_crawler(crawler.base_url) is False:
                    raise RuntimeError("Fatal error removing crawler.")

            if SLOW_DEBUG is True:
                logger.debug(f"self.num_recipes = {self.num_recipes}")
                # Sleeps for 1 second, allow for the user to watch for the crawler messing up.
                # This somewhat "throttles" how much bandwidth.  Would need more code to actually implement throttling.
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
        """Number bytes of webpages downloaded by the Crawlers."""
        return sum([c.num_get_calls for c in self.crawlers])

    def results_num_bytes_downloaded(self) -> int:
        """Number bytes downloaded by the Crawlers."""
        return sum([c.num_bytes_downloaded for c in self.crawlers])

    def generate_license_report(self) -> str:
        """Generates a report containing the licenses, websites"""
        md = ""
        # TODO: might be nice to have the report sorted by site_title
        for c in self.crawlers:
            md += c.license_report()

        return md


##### class Crawler ######################################################
# Provide a url and it will crawl the website scraping Schema.org/Recipe patterns.  It also finds another page to crawl.
class Crawler:
    """This crawls one website."""

    def __init__(
        self,
        url: str,
        recipe_url: str = "",
        license=None,
        start_url: str = "",
        site_title: str = "",
    ):
        self.base_url = url

        # self._url_list_high and self._url_list_low are the crawler frontier
        # start_url and url are seeds
        # list of urls that have a better chance to have recipes
        self._url_list_high: List = []
        if start_url:
            logger.debug(f"Add start_url: {start_url}")
            self._url_list_high.append(start_url)
        else:
            self._url_list_high.append(url)
            logger.debug(f"Add url: {url}")

        # This is a list of anchors found on the site that will be randomly pulled from to continue crawling.
        self._url_list_low: List = []

        # this is a list of dictionaries
        self.recipe_json: List = []
        # stores the HTML content  -  NOTE: Nothing is done with this content at the present time.
        self.html_pages: List = []
        # list of urls already visited, so as to not visit again
        self.been_there_urls: List = []
        # store the number of requests.get() calls made
        self.num_get_calls = 0
        # store the number of bytes downloaded
        #    skips robots.txt, counts compressed bytes when those are reported by server, otherwise counts uncompressed bytes.
        #    This is an inaccurate metric.
        self.num_bytes_downloaded = 0

        # Website's Title
        self.site_title = site_title

        # url stem that should have recipes
        # something like:  http://www.example.com/recipes/
        self._recipe_url = recipe_url
        if recipe_url is None:
            self._recipe_url = ""

        # _license will either be a URL (string)
        self._license: str = ""
        if license and license.lower() != "proprietary":
            if URLTest().is_absolute_url(license):
                self._license = license

        robots_txt_url = urllib.parse.urljoin(url, "robots.txt")

        try:
            robots = reppy.robots.Robots.fetch(robots_txt_url)
        except reppy.exceptions.ConnectionExceptions as e:
            raise RecipeCrawlerNetworkError(e)
        self.agent = robots.agent("*")
        logger.debug(f"Reading robots.txt at: {robots_txt_url}")

        self.urltest = URLTest(url)

    def crawl(self) -> int:
        """This crawls a single page.
        returns the number of recipes found"""
        logger.debug("called crawl()")
        num_recipes = 0

        response = self._download_page()
        scrapings = self._scrape_page(response)
        self._mine_anchors(response)

        logger.debug(
            f"High list: {len(self._url_list_high)} Low list: {len(self._url_list_low)}"
        )
        if scrapings is not None:
            if isinstance(scrapings, dict):
                similar_idx = self._has_similar_recipe(scrapings)
                if similar_idx == -1:
                    # no similar recipe
                    self.recipe_json.append(scrapings)
                    num_recipes += 1
                    # logger.debug(f"Adding a recipe: {scrapings['name']}")
                    self.html_pages.append(response.text)
                else:
                    logger.debug(f"Skipping a similar recipe:{scrapings['name']}")
                    logger.debug(f"URL 1: {scrapings['url']}")
                    logger.debug(f"URL 2: {self.recipe_json[similar_idx]['url']}")
            else:  # for lists
                raise NotImplemented(
                    "Recipes websites currently don't have multiple recipes on one webpage, not sure of the implications."
                )
                num_recipes += len(scrapings)
                self.recipe_json.extend(scrapings)
                self.html_pages.append(response.text)

        return num_recipes

    def _has_similar_recipe(self, recipe: Dict) -> int:
        """Test if there is already a similar recipe

        return the index number in self.recipe_json of a similar
        returns -1 means no recipe found."""
        # logger.debug("calling Crawler._has_similar_recipe()")
        if len(self.recipe_json) < 1:
            return -1

        for i in range(len(self.recipe_json)):
            r = self.recipe_json[i]
            # logger.debug(f'R == {r}, I == {i}')
            if r.get("url") == recipe.get("url"):
                return i

            if (
                r.get("name") == recipe.get("name")
                and r.get("recipeInstructions") == recipe.get("recipeInstructions")
                and r.get("recipeIngredient") == recipe.get("recipeIngredient")
            ):
                return i

        logger.debug("No similar recipe.")
        return -1

    def _download_page(self) -> requests.models.Response:
        """
        Get an url from the list and download a webpage

        returns a requests.Response object
        """
        # logger.debug("called _download_page()")
        url = None
        while not url:
            # this picks a url
            if len(self._url_list_high) > 0:
                url = self._url_list_high.pop()
            elif len(self._url_list_low) > 0:
                # randomly get an item off the low list
                r = randint(0, len(self._url_list_low) - 1)
                url = self._url_list_low.pop(r)
            else:
                raise AnchorListsEmptyError("The anchor lists are empty.")

            # check if this URL has already been visited.
            #  if url in self.been_there_urls:
            #    url = None

            # The other way to deal with this would be to check if the URL is already in the list, don't add it.

        self.been_there_urls.append(url)
        logger.debug(f"Visiting {url}")

        self.num_get_calls += 1
        resp = requests.get(url, headers=REQUESTS_HEADERS, timeout=5)
        if resp.headers.get("Content-Length"):
            # compressed size
            self.num_bytes_downloaded += int(resp.headers.get("Content-Length"))
        else:
            # uncompressed size
            self.num_bytes_downloaded += len(resp.text)

        return resp

    def _scrape_page(self, response: requests.Response):
        """
        scrapes a page
        input: response is a requests.models.Response object from requests.get()

        return dict or List, if it is empty it will be None
        """
        logger.debug("called Crawler._scrape_page()")
        recipe = scrape_schema_recipe.loads(response.text)
        if len(recipe) > 0:
            if len(recipe) == 1:
                # if the schema output doesn't already have the url/license, add those to the output

                if recipe[0].get("url") is None:
                    recipe[0]["url"] = response.url

                if self._license and recipe[0].get("license") is None:
                    recipe[0]["license"] = self._license
                return recipe[0]
            else:
                return recipe

        return None

    def _mine_anchors(self, response: requests.models.Response) -> None:
        """Mines anchors from the webpage response.

        This takes all of the anchors and evaluates them and places them into the proper lists."""
        # get all the anchor tags
        # logger.debug("called _mine_anchors()")
        soup = BeautifulSoup(response.text, "html.parser")
        all_anchors = soup.find_all("a")
        for a in all_anchors:
            href = a.get("href")
            score, url = self._rank_url(href)
            # NOTE: Should I check if the webpage is already in the list?
            # logger.debug(f"score: {score}  href: {href}")

            if score == 1:  # High score
                # check that the URL isn't in the list before adding url
                if url not in self._url_list_high:
                    self._url_list_high.append(url)
            elif score == 0:  # Low score
                # check that the URL isn't in the list before adding url
                if url not in self._url_list_low:
                    self._url_list_low.append(url)

            # otherwise skip the URL, especially the ones with a -1 score

    def _rank_url(self, url: str) -> Tuple[int, str]:
        """Rank the url's likelihood of having recipe data.
        parameter: url

        returns tuple (score, absolute_url)
            score as an integer
                 1  - likely to have a recipe
                 0  - unlikely to have a recipe
                -1 or less - do not visit
                    (There are numerous reasons to disquality a URL).
        """

        # must be a string
        if not isinstance(url, str):
            return (-1, url)

        # these hrefs won't lead to a webpage link
        if url.startswith(("#", "javascript:", "mailto:")):
            return (-2, url)

        if self.urltest.is_absolute_url(url):
            # is the URL on the same domain?
            if not self.urltest.is_same_domain(url):
                return (-3, url)
        else:
            # convert relative URL into an absolute URL
            url = urllib.parse.urljoin(self.base_url, url)

        # Has the crawler already been to (visited) this URL?
        if url in self.been_there_urls:
            return (-4, url)

        # Check if robots.txt rules allow going to this URL
        #        if self.robotparse.can_fetch(USER_AGENT_ROBOTS, url) is False:
        #        if self.robotparse.can_fetch("*", url) is False:
        if self.agent.allowed(url) is False:
            return (-5, url)

        if self._recipe_url != "" and url.startswith(self._recipe_url):
            return (1, url)

        return (0, url)

    # TODO Needs to also report the author because some licenses require attribution.
    def license_report(self) -> str:
        """Generate a license report

        returns a string in markdown format"""
        # Does this have any recipe stored?
        if len(self.recipe_json) < 1:
            # No recipe content
            return ""

        # store markdown text in md
        md = f"## {self.site_title}\n\n"
        md += f"Website URL: <{self.base_url}>\n"
        # is this a url or not value
        if self._license:
            # get the title of the license
            # by downloading the license URL and scraping the its <title> tag
            resp = requests.get(self._license)

            if resp.headers.get("Content-Length"):
                # compressed size
                self.num_bytes_downloaded += int(resp.headers.get("Content-Length"))
            else:
                # uncompressed size
                self.num_bytes_downloaded += len(resp.text)

            soup = BeautifulSoup(resp.text, features="lxml")
            try:
                license_title = soup.title.text.replace("\n", "")
                md += f"License: [{license_title}]({self._license})\n"
            except AttributeError:
                # without license title
                md += f"License: <{self._license}>\n"

        recipe_names_urls_authors = [
            (recipe["name"], recipe["url"], recipe.get("author"))
            for recipe in self.recipe_json
        ]
        md += "Recipes:\n"
        recipe_names_urls_authors.sort()
        for name, url, author in recipe_names_urls_authors:
            md += f" * [{name}]({url})"
            if author:
                if isinstance(author, str):
                    # a string type is outside the schema.org/Recipe spec, but Food.com website behaves this way
                    md += f" by {author}"
                elif isinstance(author, dict) and author.get("name"):
                    if author.get("url"):
                        md += f" by [{author['name']}]({author['url']})"
                    else:
                        md += f" by {author.get('name')}"

            md += "\n"
        md += "\n"

        return md


def load_website_sources_list(
    config_filename: str = "website_sources.yaml",
) -> List[Dict]:
    """
    Loads a list of websites with attributes about those websites as a List of Dicts.
    """
    # loads the websites to scrape from
    with open(config_filename, "r") as fp:
        return [data for data in yaml.safe_load_all(fp)]


### RecipeScrapersCrawler ############################################################################################


class RecipeScrapersCrawler(Crawler):
    """Crawlers that rely upon the recipe_scraper library."""

    def __init__(
        self,
        url: str,
        recipe_url: str = "",
        license=None,
        start_url: str = "",
        site_title: str = "",
    ):
        # Bypass requests.get by calling the website's class directly.
        # NOTE: Other websites could be supported.  That support would go here
        #       and in the MultiCrawler.add_crawler()
        # CHECK FOR SUPPORT FROM scrape-schema-recipe BEFORE ADDING A recipe-scraper DRIVER
        if "myplate.gov" in url:
            self.ScraperDriver = recipe_scrapers.USDAMyPlate
        elif "healthyeating.nhlbi.nih.gov" in url:
            self.ScraperDriver = recipe_scrapers.NIHHealthyEating
        else:
            raise NotImplemented(f"Website '{url}' has not been implemented.")

        super().__init__(url, recipe_url, license, start_url, site_title)

    def _scrape_page(self, response: requests.models.Response) -> Dict:
        """
        scrapes a page
        input: response is a requests.models.Response object from requests.get()

        return dict or List, if it is empty it will be None
        """
        logger.debug("called RecipeScrapersCrawler._scrape_page()")
        with StringIO(response.text) as fp:
            # NOTE does recipe_scraper_obj need to be kept?
            recipe_scraper_obj = self.ScraperDriver(fp)

            dict = self._convert_recipe_scraper_to_schema_dict(
                recipe_scraper_obj, response.url
            )
            return dict

    # TODO: This function will need to be rewritten based on how exceptions work in recipe-scrapers versions after 13.3.0
    def _convert_recipe_scraper_to_schema_dict(self, rs, url: str) -> Union[Dict, None]:
        """Convert recipe-scraper object into a recipe schema dictionary"""
        logger.debug("called _convert_recipe_scraper_to_schema_dict()")
        d = {}

        # NOTE: All of these tags are the text versions of the tags.

        try:
            # this is a list of strings
            d["recipeIngredient"] = rs.ingredients()
        except (AttributeError, ElementNotFoundInHtml):
            return None

        d["name"] = rs.title()

        # this is the list version of the tag
        d["recipeInstructions"] = rs.instructions().split("\n")

        try:
            if rs.total_time():
                # converts minutes into and ISO duration
                # 75 minutes becomes "PT1H15M"
                d["totalTime"] = isodate.duration_isoformat(
                    timedelta(minutes=rs.total_time())
                )
        except (NotImplemented, ElementNotFoundInHtml):
            pass

        try:
            if rs.image():
                d["image"] = rs.image()
            # BUG in recipe_scraper:  https://healthyeating.nhlbi.nih.gov/recipedetail.aspx?linkId=16&cId=6&rId=236 produces AttributeError which it shouldn't
        except (ElementNotFoundInHtml, AttributeError):
            pass

        try:
            if rs.yields():
                d["recipeYield"] = rs.yields()
        except ElementNotFoundInHtml:
            pass

        # these are other additions to the dictionary not really relevant to content from the recipe_scraper library

        d["@context"] = "https://schema.org"
        d["@type"] = ("Recipe",)
        if self._license is not None:
            d["license"] = self._license

        d["url"] = url

        return d


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


### Exceptions ###########################################################


class RecipeCrawlerException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"recipe_crawler exception: {self.message}"


class AnchorListsEmptyError(Exception):
    """Normal exception when the anchor lists are empty."""

    def __init__(self, message):
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"AnchorListsEmptyError: {self.message}"


class RecipeCrawlerNetworkError(RecipeCrawlerException):
    """Network Error"""

    def __init__(self, other_err: str):
        message = f"Network Error: {other_err}"
        super().__init__(message)


### Exceptions related to the CLI ###
class UserDuplicateFilenameError(Exception):
    """Duplicate filename error"""

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(filename)

    def __str__(self) -> str:
        return f"UserDuplicateFilenameError: There is already a file named '{self.filename}'"


class UserEmptyWebsiteListError(Exception):
    """Empty Website List error"""

    def __init__(self, message=None):
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return (
            "UserDuplicateFilenameError: Website List is empty, filter is too narrow."
        )


##########  MAIN  #########################################################
def main(sys_args: List = sys.argv[1:]) -> None:
    website_sources_list: List = []

    parser = argparse.ArgumentParser(
        description="Recipe Crawler to that saves a cookbook to a JSON file."
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="website_sources.yaml",
        help="website configuration YAML file",
    )
    parser.add_argument(
        "-f", "--filter", type=str, help="filter names of websites to crawl"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit of number of recipes to collect (default: 20)",
    )
    parser.add_argument("-o", "--output", type=str, help="Output to a JSON file")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    if args.output:
        if not args.output.lower().endswith(".json"):
            args.output += ".json"

        if os.path.exists(args.output):
            raise UserDuplicateFilenameError(filename=args.output)
    else:
        # create unique cookbook filename
        # this serves as a repository for the crawler.
        args.output = "cookbook.json"
        i = 0
        while os.path.exists(args.output):
            i += 1
            args.output = f"cookbook-{i}.json"

    website_sources_list = load_website_sources_list()

    if args.filter:
        # argument filter the url list
        def arg_in_list(a):
            return args.filter.lower() in a["site"]["url"]

        website_sources_list = list(filter(arg_in_list, website_sources_list))
        # Alternatively:
        # website_sources_list = [args.filter.lower() in a["site"]["url"] for a in website_sources_list]

        logger.info(
            f"filtering source list based on '{args.filter}' to {len(website_sources_list)} number of items"
        )

        if len(website_sources_list) == 0:
            # logger.info("This filter filtered out all the websites.  Exiting.")
            # sys.exit(0)
            raise UserEmptyWebsiteListError

    # log to a file
    logger.add(f"recipe_crawler_{datetime.now().isoformat()}.log")

    start_time = pendulum.now()

    logger.info(f"Crawling for {args.limit} recipes.")

    mc = MultiCrawler(args.limit)

    for source in website_sources_list:
        # logger.debug('KEYS: {}'.format(source['site'].keys()))

        logger.debug(f"Adding crawler for: {source['site']['url']}")
        mc.add_crawler(
            source["site"]["url"],
            source["site"].get("recipe_url"),
            source["site"].get("license"),
            # this is a URL the one that most-likely to get to recipes quickly, such as an index or landing pages for recipes.
            source["site"].get("start_url"),
            source["site"].get("title"),
        )

    mc.run()

    recipes_dict = mc.results_dict()

    # save to file
    with open(args.output, "w") as fp:
        json.dump(recipes_dict, fp)

    license_filename = f"license-{args.output[:-5]}.md"
    with open(license_filename, "w") as fp:
        fp.write(mc.generate_license_report())

    logger.info(f"Wrote files '{args.output}' and '{license_filename}'.")


    logger.info(f"Number of web pages downloaded: {mc.results_num_get_calls()}")

    logger.info(
        f"Number of bytes downloaded: {mc.results_num_bytes_downloaded()/2**20:.3f} MiB*"
    )
    logger.info("  * Metric is not accurate.")
    runtime = pendulum.now().diff(start_time)
    # README.md row printer, INCOMPLETE
#    logger.info(f"row:  | {__version__} | {args.limit} | | {mc.results_num_get_calls()} | | {mc.results_num_get_calls() / args.limit} | |")
    logger.info(f"Program's Runtime: {runtime.in_words()}")


if __name__ == "__main__":
    main()


