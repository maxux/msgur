import dulwich.repo
from datetime import datetime

class Repository:
    def __init__(self, enabled: bool = True, path: str = "."):
        self.enabled = enabled
        self.path = path

        self.commit = None
        self.revision = None
        self.created = None

        if enabled:
            self.parse()

    def parse(self):
        try:
            repo = dulwich.repo.Repo(self.path)
            head = repo.head()
            self.commit = head.decode("utf-8")
            self.revision = self.commit[:12]

            commit = repo[head]
            self.created = datetime.fromtimestamp(commit.commit_time)

        except dulwich.errors.NotGitRepository as error:
            print("[-] revision: no repository found")
