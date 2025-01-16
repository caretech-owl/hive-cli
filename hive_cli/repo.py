import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from git import Remote, Repo
from pydantic import SecretStr

from hive_cli.data import HiveData, RepoState

_LOGGER = logging.getLogger(__name__)


class RepoController:
    def __init__(self, hive: HiveData) -> None:
        self.repo = (
            Repo(hive.settings.hive_repo) if hive.settings.hive_repo.exists() else None
        )
        self.hive = hive
        self.update_state()

    def init_repo(self) -> None:
        repo_path = self.hive.settings.hive_repo
        repo_url = self.hive.settings.hive_url
        _LOGGER.debug("Cloning %s to %s", repo_url, repo_path)
        repo_path.mkdir()
        self.repo = Repo.init(repo_path)
        origin = self.repo.create_remote("origin", repo_url)
        origin.fetch()
        self.repo.create_head("main", origin.refs.main).set_tracking_branch(
            origin.refs.main
        ).checkout()
        origin.pull()
        self.update_state()

    def update_repo(self) -> None:
        if not self.repo:
            _LOGGER.error("No repo found at %s", self.hive.settings.hive_repo)
            self.hive.repo_state = RepoState.NOT_FOUND
            return None
        self.reset_repo()
        self.hive.repo_state = RepoState.UPDATING
        self.repo.remote("origin").fetch()
        self.repo.remote("origin").pull()
        self.repo.heads.main.checkout()

    def remote_changes(self, file_path: Path) -> bool:
        cmd = [
            "git",
            "-C",
            self.hive.settings.hive_repo.as_posix(),
            "diff",
            "--quiet",
            "origin/main",
            "HEAD",
            "--",
            file_path.as_posix(),
        ]
        _LOGGER.debug("Running command %s", " ".join(cmd))
        return subprocess.call(cmd) != 0

    def reset_repo(self) -> None:
        if not self.repo:
            _LOGGER.error("No repo found at %s", self.hive.settings.hive_repo)
            self.hive.repo_state = RepoState.NOT_FOUND
            return None
        _LOGGER.debug("Resetting repo to origin/main")
        for untracked in self.repo.untracked_files:
            (self.hive.settings.hive_repo / untracked).unlink()
        self.repo.head.reset(index=True, working_tree=True)
        self.repo.heads.main.checkout()
        self.update_state()

    def commit_changes(self) -> None:
        if not self.repo:
            _LOGGER.error("No repo found at %s", self.hive.settings.hive_repo)
            self.hive.repo_state = RepoState.NOT_FOUND
            return None
        branch_name = (
            f"{self.hive.settings.hive_id[:3]}_{self.hive.settings.hive_id[-3:]}-"
            f"{int(datetime.now().timestamp())}"
        )
        _LOGGER.debug("Committing changes to remote branch %s", branch_name)
        self.repo.create_head(branch_name).checkout()
        self.repo.index.add("*")
        self.repo.index.commit(
            "Changes made by hive-cli on " + datetime.now().isoformat()
        )
        origin = self.repo.remote("origin")

        with TokenizedRemote(origin, self.hive.settings.github_token) as tokenized:
            _LOGGER.debug("Pushing changes to remote")
            tokenized.push(branch_name, kill_after_timeout=2.0)
        self.update_state()

    def update_state(self) -> None:
        if not self.repo:
            self.hive.repo_state = RepoState.NOT_FOUND
            return None

        _LOGGER.debug("Fetching origin from %s", self.hive.settings.hive_url)
        self.repo.remote("origin").fetch()

        if self.repo.active_branch.name != "main":
            self.hive.repo_state = RepoState.CHANGES_COMMITTED
        elif datetime.fromtimestamp(
            self.repo.head.commit.committed_date
        ) < datetime.fromtimestamp(self.repo.remote().refs.main.commit.committed_date):
            self.hive.repo_state = RepoState.UPDATE_AVAILABLE
        elif (
            self.repo.is_dirty()
            or len(self.repo.untracked_files) > 0
        ):
            self.hive.repo_state = RepoState.CHANGED_LOCALLY
        else:
            self.hive.repo_state = RepoState.UP_TO_DATE


class TokenizedRemote:

    def __init__(self, remote: Remote, token: str) -> None:
        self.remote: Remote = remote
        self.tmp_remote: Remote | None = None
        self.token: SecretStr | None = token

    def __enter__(self) -> Remote:
        if self.token is None:
            _LOGGER.debug("Using existing remote without token")
            url = self.remote.url
        else:
            _LOGGER.debug("Creating temporary remote with token")
            url = self.remote.url.replace(
                "https://", f"https://{self.token.get_secret_value()}@"
            )
            if "github.com" not in url:
                msg = "Only GitHub remotes are supported"
                raise AssertionError(msg)
        self.tmp_remote = self.remote.repo.create_remote("tmp", url)
        return self.tmp_remote

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        _LOGGER.debug("Removing temporary remote")
        if self.tmp_remote is not None:
            self.tmp_remote.remove(self.remote.repo, self.tmp_remote.name)
