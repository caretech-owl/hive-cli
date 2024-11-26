from hive_cli.config import load_settings()
from git import Repo

def init_repo():
    repo_path = load_settings().hive_repo
    repo_url = load_settings().hive_url
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    origin = repo.create_remote('origin', repo_url)
    origin.fetch()
    repo.create_head("main", origin.refs.main).set_tracking_branch(origin.refs.main).checkout()
    origin.pull()

def update_repo():
    repo = Repo(load_settings().hive_repo)
    origin = repo.remote('origin')
    origin.fetch()
    origin.pull()
