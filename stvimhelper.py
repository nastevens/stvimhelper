from atlassian import Confluence as ConfluenceApi, Jira as JiraApi
from dataclasses import dataclass
from github import Github as GithubApi
from typing import Any, Optional, Set, Type
from urllib.parse import urlparse
import click
import os
import re


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


class ServiceMatch:
    url: str

    @classmethod
    def url_matches(cls, query):
        if cls.url:
            query_netloc = urlparse(query).netloc
            our_netloc = urlparse(cls.url).netloc
            return query_netloc == our_netloc
        return False


class AtlassianService(ServiceMatch):
    url = "https://smartthings.atlassian.net"

    def __init__(self):
        super().__init__()
        self.username = os.environ["ATLASSIAN_ID"]
        self.password = os.environ["ATLASSIAN_TOKEN"]

    @property
    def api(self):
        return ConfluenceApi(
            url=self.url,
            username=self..username,
            password=self..password,
            cloud=True,
        )


@query_handler
class Confluence:
    service: Type[ServiceMatch] = AtlassianService

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

    def link(self) -> str:
        base = self.page["_links"]["base"]
        webui = self.page["_links"]["webui"]
        return base + webui

    def title(self) -> str:
        return self.page["title"]

    def review(self) -> str:
        return f"[[{self.link()}|Confluence >> {self.title()}]]"


@query_handler
class Jira:
    service: Type[ServiceMatch] = AtlassianService

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

    def link(self) -> str:
        return f"{self.service.url}/browse/{self.issue_key}"

    def summary(self) -> str:
        return self.issue["fields"]["summary"]

    def review(self) -> str:
        return f"[[{self.link()}|{self.issue_key} >> {self.summary()}]]"


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
class PrInfo:
    org: str
    repo_name: str
    prno: int

    @property
    def repo(self):
        return f"{self.org}/{self.repo_name}"

    @property
    def path(self):
        return f"/{self.org}/{self.repo_name}/pull/{self.prno}"


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
                    repo_name=match.group(2),
                    prno=int(match.group(3)),
                )
        return None

    def __init__(self, query):
        api = self.service().api
        self.pr_info = self.get_pr_info(query)
        self.pr = api.get_repo(self.pr_info.repo).get_pull(self.pr_info.prno)
        self.query = query

    def link(self) -> str:
        return f"{self.service.url}{self.pr_info.path}"

    def title(self) -> str:
        return self.pr.title

    def review(self) -> str:
        return (
            f"[[{self.link()}|{self.pr_info.repo_name} "
            f"#{self.pr_info.prno} >> {self.title()}]]"
        )


@query_handler
class GithubPullRequest(PullRequest):
    service = GithubService


@query_handler
class EcodesamsungPullRequest(PullRequest):
    service = EcodesamsungService


@dataclass
class IssueInfo:
    org: str
    repo_name: str
    prno: int

    @property
    def repo(self):
        return f"{self.org}/{self.repo_name}"

    @property
    def path(self):
        return f"/{self.org}/{self.repo_name}/pull/{self.prno}"

class Issue:
    service: Type[ServiceMatch]

    @classmethod
    def can_handle(cls, query) -> bool:
        return bool(cls.get_issue_info(query))

    @classmethod
    def get_issue_info(cls, query) -> Optional[IssueInfo]:
        pass


# @query_handler
# class GithubIssue(Issue):
#     service = GithubService


# @query_handler
# class EcodesamsungIssue(Issue):
#     service = EcodesamsungService


@click.group()
def cli():
    pass


@cli.command()
@click.argument("query")
def review(query):
    handler = QueryHandler.find_handler(query)
    if handler:
        print(handler(query).review())
