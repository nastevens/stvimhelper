from atlassian import Confluence as ConfluenceApi, Jira as JiraApi
from typing import Any, Optional, Set
from urllib.parse import urlparse
import click
import os
import re


def is_atlassian_url(query):
    split = urlparse(query)
    return split.netloc == "smartthings.atlassian.net"


class QueryHandler:
    _handlers: Set[Any] = set()

    def __call__(self, cls):
        QueryHandler._handlers.add(cls)
        return cls

    @classmethod
    def find_handler(cls, query) -> Optional[type]:
        for handler in cls._handlers:
            if handler.can_handle(query):
                return handler
        return None


query_handler = QueryHandler()


class Atlassian:
    URL = "https://smartthings.atlassian.net"

    def __init__(self):
        self.username = os.environ["ATLASSIAN_ID"]
        self.password = os.environ["ATLASSIAN_TOKEN"]


@query_handler
class Confluence(Atlassian):
    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_page_id(query))

    @staticmethod
    def get_page_id(query) -> Optional[str]:
        path = urlparse(query).path
        page_id = re.match(r"(?:/wiki/spaces/[^/]+/pages/)?(\d+)", path)
        if is_atlassian_url(query) and page_id:
            return page_id.group(1)
        return None

    def __init__(self, query):
        super().__init__()
        api = ConfluenceApi(
            url=Atlassian.URL,
            username=self.username,
            password=self.password,
            cloud=True,
        )
        self.page_id = self.get_page_id(query)
        self.page = api.get_page_by_id(self.page_id)
        self.query = query

    def link(self) -> str:
        base = self.page["_links"]["base"]
        webui = self.page["_links"]["webui"]
        return base + webui

    def title(self) -> str:
        return self.page["title"]

    def review(self) -> str:
        return f"[[{self.link()}|Confluence >> {self.title()}]]"


@query_handler
class Jira(Atlassian):
    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_issue_key(query))

    @staticmethod
    def get_issue_key(query) -> Optional[str]:
        path = urlparse(query).path
        if is_atlassian_url(query):
            key = re.match(r"(?:/browse/)?([A-Za-z0-9]+-\d+)", path)
            if key:
                return key.group(1)
        else:
            key = re.match(r"[A-Za-z][A-Za-z0-9]*-\d+", path)
            if key:
                return key.group(0)
        return None

    def __init__(self, query):
        super().__init__()
        api = JiraApi(
            url=Atlassian.URL,
            username=self.username,
            password=self.password,
            cloud=True,
        )
        self.issue_key = self.get_issue_key(query)
        self.issue = api.issue(self.issue_key)
        self.query = query

    def link(self) -> str:
        return f"{Atlassian.URL}/browse/{self.issue_key}"

    def summary(self) -> str:
        return self.issue["fields"]["summary"]

    def review(self) -> str:
        return f"[[{self.link()}|{self.issue_key} >> {self.summary()}]]"


@click.group()
def cli():
    pass


@cli.command()
@click.argument("query")
def review(query):
    handler = QueryHandler.find_handler(query)
    if handler:
        print(handler(query).review())
