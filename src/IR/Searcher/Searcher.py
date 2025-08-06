from elasticsearch import Elasticsearch

from src.IR.config.Elasic_Config_Loader import Elasic_Config_Loader


class Searcher:
    def __init__(self, index_name=None):
        """
        Initialize the searcher. Make sure the elastic search is running.
        :param index_name: No need to pass this parameter unless some particular reason. It will be loaded from config file.
        """

        # Create an instance of ConfigLoader (config file will be loaded automatically)
        config_loader = Elasic_Config_Loader()

        # Accessing configuration parameters using class methods
        elastic_search_host = config_loader.get_elastic_search_host()
        elastic_search_port = config_loader.get_elastic_search_port()
        elastic_search_index = config_loader.get_index_name()

        if index_name is None:
            self.index_name = elastic_search_index
        else:
            self.index_name = index_name

        # Create an instance of Elasticsearch client
        self.es_client = Elasticsearch('http://' + elastic_search_host + ':' + str(elastic_search_port),
                                       # http_auth=("username", "password"),
                                       verify_certs=False,
                                       request_timeout=10000)

    def getElasicSearchClient(self):
        return self.es_client

    def search(self, project, buggy_commit, query, top_K_results=10):
        search_query = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "project": project
                            }
                        },
                        {
                            "match": {
                                "buggy_commit": buggy_commit
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "source_code": {
                                    "query": query,
                                    "analyzer": "stop"  # Specify the custom analyzer here
                                }
                            }
                        }
                        # You can add more "should" clauses here if needed.
                    ]
                }
            }

        # search_results = self.es_client.search(index=self.index_name, body=search_query)
        search_results = self.es_client.search(index=self.index_name, query=search_query, size=top_K_results, _source=["file_url"])

        results_file_urls = self.compiled_search_results(search_results)

        return results_file_urls

    def search_field(self, project, buggy_commit, field_to_search, top_K_results=10, field_to_return = ["file_url"]):
        search_query = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "project": project
                            }
                        },
                        {
                            "match": {
                                "buggy_commit": buggy_commit
                            }
                        },
                        {
                            "match": {
                                "file_url": field_to_search
                            }
                        }
                    ]
                }
            }

        # search_results = self.es_client.search(index=self.index_name, body=search_query)
        search_results = self.es_client.search(index=self.index_name, query=search_query, size=top_K_results, _source=field_to_return)

        result_dict_arr = []

        for hit in search_results["hits"]["hits"]:
            source = hit.get("_source", {})

            temp_dict = {}
            for field in field_to_return:
                temp_dict[field] = source.get(field)

            result_dict_arr.append(temp_dict)

        return result_dict_arr

    def search_Extended(self, project, buggy_commit, query, top_K_results=10, field_to_return=["file_url"]):
        search_query = {
                "bool": {
                    "must": [
                        {
                            "match": {
                                "project": project
                            }
                        },
                        {
                            "match": {
                                "buggy_commit": buggy_commit
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "source_code": query
                            }
                        }
                        # You can add more "should" clauses here if needed.
                    ]
                }
            }

        # search_results = self.es_client.search(index=self.index_name, body=search_query)
        search_results = self.es_client.search(index=self.index_name, query=search_query, size=top_K_results, _source=field_to_return)

        result_dict = []

        for hit in search_results["hits"]["hits"]:
            doc_id = hit.get("_id")
            source = hit.get("_source", {})
            project = source.get("project")
            source_code = source.get("source_code")
            file_url = source.get("file_url")
            buggy_commit = source.get("buggy_commit")
            bm_score = hit.get("_score")

            result_dict.append({"project": project, "source_code": source_code, "file_url": file_url, "buggy_commit": buggy_commit, "doc_id": doc_id, "bm25_score": bm_score})

        return result_dict

    def compiled_search_results(self, search_results):

        suggested_all_source_files = []

        for hit in search_results["hits"]["hits"]:
            source = hit.get("_source", {})
            suggested_source_file = source.get("file_url")

            suggested_all_source_files.append(suggested_source_file)

        return suggested_all_source_files


if __name__ == '__main__':
    # Create an instance of Searcher
    searcher = Searcher()

    # Search for a query
    top_K_results = 10
    # TODO: Update this example for your project and commit
    search_results = searcher.search("aspectj", "9319e34", "AjBuildManager", 10)

    # Print the search results
    print(search_results)