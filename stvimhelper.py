# Copyright (c) 2021, Nick Stevens <nick@bitcurry.com>
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# http://www.apache.org/license/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or http://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from atlassian import Confluence as ConfluenceApi, Jira as JiraApi
from dataclasses import dataclass
from github import Github as GithubApi
from typing import Any, Optional, Set, Type
from urllib.parse import urlparse
import click
import os
import re


class QueryHandler:
    """
    Decorator class to collect and iterate handlers
    """
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


class ServiceMatch:
    """
    Abstract class for checking that a query matches a given host location
    """
    url: str

    @classmethod
    def url_matches(cls, query):
        if cls.url:
            query_netloc = urlparse(query).netloc
            our_netloc = urlparse(cls.url).netloc
            return query_netloc == our_netloc
        return False


# --- Atlassian services ---

class AtlassianService(ServiceMatch):
    url = "https://smartthings.atlassian.net"

    def __init__(self):
        super().__init__()
        self.username = os.environ["ATLASSIAN_ID"]
        self.password = os.environ["ATLASSIAN_TOKEN"]


class ConfluenceService(AtlassianService):
    @property
    def api(self):
        return ConfluenceApi(
            url=self.url,
            username=self.username,
            password=self.password,
            cloud=True,
        )


class JiraService(AtlassianService):
    @property
    def api(self):
        return JiraApi(
            url=self.url,
            username=self.username,
            password=self.password,
            cloud=True,
        )


@query_handler
class Confluence:
    service: Type[ServiceMatch] = ConfluenceService

    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_page_id(query))

    @classmethod
    def get_page_id(cls, query) -> Optional[str]:
        path = urlparse(query).path
        if cls.service.url_matches(query):
            match = re.match(r"(?:/wiki/spaces/[^/]+/pages/)?(\d+)", path)
            if match:
                return match.group(1)
        return None

    def __init__(self, query):
        api = self.service().api
        self.page_id = self.get_page_id(query)
        self.page = api.get_page_by_id(self.page_id)
        self.query = query

    @property
    def link(self) -> str:
        base = self.page["_links"]["base"]
        webui = self.page["_links"]["webui"]
        return base + webui

    @property
    def title(self) -> str:
        return self.page["title"]

    @property
    def review(self) -> str:
        return f"[[{self.link}|Confluence >> {self.title}]]"


@query_handler
class Jira:
    service: Type[ServiceMatch] = JiraService

    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_issue_key(query))

    @classmethod
    def get_issue_key(cls, query) -> Optional[str]:
        path = urlparse(query).path
        if cls.service.url_matches(query):
            match = re.match(r"(?:/browse/)?([A-Za-z0-9]+-\d+)", path)
            if match:
                return match.group(1)
        else:
            match = re.match(r"[A-Za-z][A-Za-z0-9]*-\d+", path)
            if match:
                return match.group(0)
        return None

    def __init__(self, query):
        api = self.service().api
        self.issue_key = self.get_issue_key(query)
        self.issue = api.issue(self.issue_key)
        self.query = query

    @property
    def link(self) -> str:
        return f"{self.service.url}/browse/{self.issue_key}"

    @property
    def summary(self) -> str:
        return self.issue["fields"]["summary"]

    @property
    def review(self) -> str:
        return f"[[{self.link}|{self.issue_key} >> {self.summary}]]"


# --- Github services


class GithubService(ServiceMatch):
    url = "https://github.com"

    def __init__(self):
        super().__init__()
        self.token = os.environ["GITHUB_TOKEN"]

    @property
    def api(self):
        return GithubApi(self.token)


class EcodesamsungService(ServiceMatch):
    url = "https://github.ecodesamsung.com"

    def __init__(self):
        self.token = os.environ["ECODESAMSUNG_TOKEN"]

    @property
    def api(self):
        return GithubApi(
            self.token,
            base_url="https://github.ecodesamsung.com/api/v3"
        )


@dataclass
class GithubInfo:
    """
    Decomposed Github link, i.e. github.com/<org>/<repo>/{pull,issues}/<ident>
    """
    org: str
    name: str
    ident: int

    @property
    def repo(self):
        return f"{self.org}/{self.name}"


class PrInfo(GithubInfo):
    @property
    def path(self):
        return f"/{self.org}/{self.name}/pull/{self.ident}"


class IssueInfo(GithubInfo):
    @property
    def path(self):
        return f"/{self.org}/{self.name}/issues/{self.ident}"


class PullRequest:
    service: Type[ServiceMatch]

    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_pr_info(query))

    @classmethod
    def get_pr_info(cls, query) -> Optional[PrInfo]:
        path = urlparse(query).path
        if cls.service.url_matches(query):
            match = re.match(r"/([^/]+)/([^/]+)/pull/(\d+)", path)
            if match:
                return PrInfo(
                    org=match.group(1),
                    name=match.group(2),
                    ident=int(match.group(3)),
                )
        return None

    def __init__(self, query):
        api = self.service().api
        self.pr_info = self.get_pr_info(query)
        self.pr = api.get_repo(self.pr_info.repo).get_pull(self.pr_info.ident)
        self.query = query

    @property
    def link(self) -> str:
        return f"{self.service.url}{self.pr_info.path}"

    @property
    def title(self) -> str:
        return self.pr.title

    @property
    def review(self) -> str:
        return (
            f"[[{self.link}|{self.pr_info.name} "
            f"#{self.pr_info.ident} >> {self.title}]]"
        )


class Issue:
    service: Type[ServiceMatch]

    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_issue_info(query))

    @classmethod
    def get_issue_info(cls, query) -> Optional[IssueInfo]:
        path = urlparse(query).path
        if cls.service.url_matches(query):
            match = re.match(r"/([^/]+)/([^/]+)/issues/(\d+)", path)
            if match:
                return IssueInfo(
                    org=match.group(1),
                    name=match.group(2),
                    ident=int(match.group(3)),
                )
        return None

    def __init__(self, query):
        api = self.service().api
        self.issue_info = self.get_issue_info(query)
        self.issue = \
            api.get_repo(self.issue_info.repo).get_issue(self.issue_info.ident)
        self.query = query

    @property
    def link(self) -> str:
        return self.issue.html_url

    @property
    def title(self) -> str:
        return self.issue.title

    @property
    def review(self) -> str:
        return (
            f"[[{self.link}|{self.issue_info.name} "
            f"#{self.issue_info.ident} >> {self.title}]]"
        )


@query_handler
class GithubPullRequest(PullRequest):
    service = GithubService


@query_handler
class EcodesamsungPullRequest(PullRequest):
    service = EcodesamsungService


@query_handler
class GithubIssue(Issue):
    service = GithubService


@query_handler
class EcodesamsungIssue(Issue):
    service = EcodesamsungService


@click.group()
def cli():
    pass


@cli.command()
@click.argument("query")
def review(query):
    handler = QueryHandler.find_handler(query)
    if handler:
        print(handler(query).review)
