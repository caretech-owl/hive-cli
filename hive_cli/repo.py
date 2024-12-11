import logging
from datetime import datetime

import yaml
from git import Repo

from hive_cli.config import load_settings
from hive_cli.data import HiveData, Recipe

_LOGGER = logging.getLogger(__name__)


def init_repo() -> None:
    repo_path = load_settings().hive_repo
    repo_url = load_settings().hive_url
    _LOGGER.debug("Cloning %s to %s", repo_url, repo_path)
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    origin = repo.create_remote("origin", repo_url)
    origin.fetch()
    repo.create_head("main", origin.refs.main).set_tracking_branch(
        origin.refs.main
    ).checkout()
    origin.pull()


def update_repo() -> None:
    repo = Repo(load_settings().hive_repo)
    origin = repo.remote("origin")
    origin.fetch()
    if repo.is_dirty():
        reset_repo()
    origin.pull()


def reset_repo() -> None:
    repo = Repo(load_settings().hive_repo)
    repo.head.reset(index=True, working_tree=True)


def commit_changes() -> None:
    repo = Repo(load_settings().hive_repo)
    repo.index.add("*")
    repo.index.commit("Changes made by hive-cli on " + datetime.now().isoformat())
    repo.remote("origin").push()


def get_data() -> HiveData | None:
    settings = load_settings()
    if not settings.hive_repo.exists():
        return None

    repo = Repo(settings.hive_repo)
    _LOGGER.debug("Fetching origin from %s", {settings.hive_url})
    repo.remote("origin").fetch()

    recipe_file = settings.hive_repo / f"{settings.hive_id}.yml"
    if recipe_file.exists():
        with recipe_file.open("r") as f:
            obj = yaml.safe_load(f)
            obj["path"] = recipe_file
            recipe = Recipe.model_validate(obj)
    else:
        _LOGGER.warning("File %s not found.", recipe_file.resolve())
        recipe = None

    return HiveData(
        local_version=datetime.fromtimestamp(repo.head.commit.committed_date),
        remote_version=datetime.fromtimestamp(
            repo.remote().refs.main.commit.committed_date
        ),
        recipe=recipe,
        local_changes=repo.is_dirty(),
    )
