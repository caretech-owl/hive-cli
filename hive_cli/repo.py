from hive_cli.config import HIVE_REPO, HIVE_URL
from git import Repo

def init_repo():
    HIVE_REPO.mkdir()
    repo = Repo.init(HIVE_REPO)
    origin = repo.create_remote('origin', HIVE_URL)
    origin.fetch()
    repo.create_head("main", origin.refs.main).set_tracking_branch(origin.refs.main).checkout()
    origin.pull()

def update_repo():
    repo = Repo(HIVE_REPO)
    origin = repo.remote('origin')
    origin.fetch()
    origin.pull()
