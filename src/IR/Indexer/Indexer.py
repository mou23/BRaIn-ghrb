from elasticsearch import Elasticsearch, helpers
import subprocess
import os
import shutil

from src.IR.config.Elasic_Config_Loader import Elasic_Config_Loader


class Indexer:
    def __init__(self, index_name=None):
        """
        Initialize the indexer. Make sure the elastic search is running.
        :param index_name: No need to pass this parameter unless some particular reason. It will be loaded from config file.
        """

        # Create an instance of ConfigLoader (config file will be loaded automatically)
        self.bulk_index_array = []
        config_loader = Elasic_Config_Loader()

        # Accessing configuration parameters using class methods
        elastic_search_host = config_loader.get_elastic_search_host()
        elastic_search_port = config_loader.get_elastic_search_port()
        self.elastic_search_index = config_loader.get_index_name()

        if index_name is None:
            self.index_name = self.elastic_search_index
        else:
            self.index_name = index_name

        # Create an instance of Elasticsearch client
        self.es_client = Elasticsearch('http://' + elastic_search_host + ':' + str(elastic_search_port),
                                  # http_auth=("username", "password"),
                                  verify_certs=False,request_timeout=90,retry_on_timeout=True,max_retries=2)

    # def checkout_commit_before_fix(self, repo_path, commit_before_fix):
    #     """
    #     Checkout the commit before the fix commit
    #     :param repo_path: Path to the git repository
    #     :param fix_commit: The commit hash where the bug was fixed
    #     :return: True if successful, False otherwise
    #     """
    #     try:
    #         # Change to the repository directory
    #         original_dir = os.getcwd()
    #         os.chdir(repo_path)

    #         # Checkout the commit before the fix
    #         subprocess.run(['git', 'checkout', commit_before_fix], check=True)
            
    #         print(f"Successfully checked out commit {commit_before_fix}")
            
    #         # Return to original directory
    #         os.chdir(original_dir)
    #         return True
            
    #     except subprocess.CalledProcessError as e:
    #         print(f"Error checking out commit: {e}")
    #         os.chdir(original_dir)
    #         return False
    #     except Exception as e:
    #         print(f"Unexpected error: {e}")
    #         os.chdir(original_dir)
    #         return False

    def checkout_commit_before_fix(self, repo_path, commit_before_fix):
        """
        Checkout the commit before the fix commit
        :param repo_path: Path to the git repository
        :param fix_commit: The commit hash where the bug was fixed
        :return: True if successful, False otherwise
        """
        try:
            # Change to the repository directory
            original_dir = os.getcwd()
            os.chdir(repo_path)
            
            subprocess.run(['git', 'worktree', 'add', commit_before_fix, commit_before_fix], check=True)
            print(f"Successfully created worktree {commit_before_fix}")
            
            # Return to original directory
            os.chdir(original_dir)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error checking out commit: {e}")
            os.chdir(original_dir)
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            os.chdir(original_dir)
            return False

    def checkout_worktree_at_commit(self, repo_root: str, commit_hash: str) -> str | None:
        """
        Create a detached worktree at the given commit and return its path.
        The worktree is created under <repo_root>/_worktrees/<commit_hash>.
        """
        original_dir = os.getcwd()
        worktrees_root = os.path.join(repo_root, "_worktrees")
        worktree_dir = os.path.join(worktrees_root, commit_hash)

        try:
            os.makedirs(worktrees_root, exist_ok=True)
            os.chdir(repo_root)

            # If a stale worktree exists, remove it first
            if os.path.exists(worktree_dir):
                try:
                    subprocess.run(["git", "worktree", "remove", "--force", worktree_dir], check=True)
                except subprocess.CalledProcessError:
                    pass
                shutil.rmtree(worktree_dir, ignore_errors=True)

            # Create a detached worktree at the specific commit
            subprocess.run(["git", "worktree", "add", "--detach", worktree_dir, commit_hash], check=True)
            print(f"Created worktree at {worktree_dir} for {commit_hash}")
            return worktree_dir

        except subprocess.CalledProcessError as e:
            print(f"git worktree error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error creating worktree: {e}")
            return None
        finally:
            os.chdir(original_dir)

    def remove_worktree(self, repo_root: str, worktree_dir: str) -> None:
        """Remove the worktree and prune metadata."""
        original_dir = os.getcwd()
        try:
            os.chdir(repo_root)
            subprocess.run(["git", "worktree", "remove", "--force", worktree_dir], check=False)
            subprocess.run(["git", "worktree", "prune"], check=False)
            shutil.rmtree(worktree_dir, ignore_errors=True)
        finally:
            os.chdir(original_dir)

    def index(self, project, source_code, file_url, buggy_commit):
        document = {
            "project": project,
            "source_code": source_code,
            "file_url": file_url,
            "buggy_commit": buggy_commit
        }
        result = self.es_client.index(index=self.index_name, body=document, refresh=False)
        print(f"Indexed document with ID: {result['_id']}")

        return result

    def bulk_action(self):
        for document in self.bulk_index_array:
            yield document

    # function for bulk indexing. it is same as before. saves the doc in array and when it reaches the limit, it indexes them in bulk
    def bulk_index(self, project, source_code, file_url, buggy_commit, bulk_size=1024):
        document = {
            "project": project,
            "source_code": source_code,
            "file_url": file_url,
            "buggy_commit": buggy_commit
        }

        indexable_document = {
            "_index": self.index_name,
            "_source": document
        }
        self.bulk_index_array.append(indexable_document)

        if len(self.bulk_index_array) >= bulk_size:
            helpers.bulk(self.es_client, actions=self.bulk_action())
            # print(f"Indexed {bulk_size} documents in bulk.")
            self.bulk_index_array = []

    def refresh(self):
        if len(self.bulk_index_array) > 0:
            helpers.bulk(self.es_client, actions=self.bulk_action())
            # print(f"Indexed {len(self.bulk_index_array)} documents in bulk.")
            self.bulk_index_array = []

        self.es_client.indices.refresh(index=self.index_name)

    def __del__(self):
        self.refresh()
