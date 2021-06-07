#!/usr/bin/env python3

import unittest
import recipe_crawler

## Test for the URLTest class
class TestURLTest(unittest.TestCase):
    def setUp(self) -> None:
        self.urltest = recipe_crawler.URLTest("https://www.example.com/")

    def test_is_absolute_url_true(self):
        assert self.urltest.is_absolute_url("http://www.example.com/")
        assert self.urltest.is_absolute_url("https://www.example.com/")

    def test_is_absolute_url_false(self):
        assert self.urltest.is_absolute_url("#") is False
        assert self.urltest.is_absolute_url("javascript:on_click()") is False
        assert self.urltest.is_absolute_url("/relative_url") is False

    def test_is_same_domain_true(self):
        assert self.urltest.is_same_domain("https://www.example.com/tacos/")
        # fixed in version 0.0.2
        assert self.urltest.is_same_domain("https://WWW.EXAMPLE.COM/")

    def test_is_same_domain_false(self):
        assert (
            self.urltest.is_same_domain("https://www.somedifferentdomain.com/") is False
        )
        assert (
            self.urltest.is_same_domain("https://www.somedifferentdomain.com/tacos/")
            is False
        )


if __name__ == "__main__":
    unittest.main()
