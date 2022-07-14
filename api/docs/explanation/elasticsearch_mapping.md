Mapping database values to Elasticsearch fields

The [indexer](https://github.com/WordPress/openverse-api/blob/24b9416ae4ab8050084862d2ee2a6e1ef66b681a/ingestion_server/ingestion_server/indexer.py) takes the data from the Postgres database and converts it to Elasticsearch documents using mappings. Before May 2022, the mapping was set to dynamic, which is more flexible, but has worse performance and has caused some problems as noted by @dhruvkb in this [PR comment](https://github.com/WordPress/openverse-api/pull/684#issuecomment-1119750842).

The [very first version of the es_mapping](https://github.com/cc-archive/cccatalog-api/blob/a0a0dd283144acd447ef344a4cdee5d8fdca699a/es-syncer/elasticsearch_models.py) uses ORM-like elasticsearch_dsl(version 6.1) to set the mappings. Elasticsearch DSL, the high-level Python library for interacting with Elasticsearch, provides a great experience when writing search queries. It also looks like writing mappings using it can be really pythonic. However, it also has some drawbacks that are significant for Openverse:

> Create mapping manually instead of using Elasticsearch DSL’s ORM-esque interface. It doesn’t provide access to low-level Elasticsearch features that we need, like boolean similarity. The interface also changes completely every time there’s a new version of Elasticsearch.

[Commit message by aldenstpage](https://href.li/?https://github.com/cc-archive/cccatalog-api/commit/11e05c4e234fa071cb5236b5a0d9848232e6882b)

Specifically, to fine-tune the search relevancy, it was necessary to change the title similarity from the default BM25 algorithm to boolean. This allowed to use ranking features and also stop repetitions in the title from worsening the search result quality (‘cat cat cat’ would be at the top of the results with theBM25 algorithm, but fully disabling ranking on it would cause other rankings to be even worse). You can find more historic details in the cc-archive repository: [PR: Phrase relevance improvements](https://github.com/cc-archive/cccatalog-api/pull/281).

For better low-level mapping customization, the ORM-like mapping definitions were replaced by the mappings in [es_mappings.py](https://github.com/WordPress/openverse-api/blob/270b086095ba125fa26e04bf27dff3ab6994e025/ingestion_server/ingestion_server/es_mapping.py), which override the elasticsearch_models.py definitions (in [this PR](https://github.com/cc-archive/cccatalog-api/pull/391)).

The first dictionary mapping was using the defaults values that Elasticsearch DSL uses. By default, it uses the `text` + `keyword` mult-field for string values. It is useful to have text+keyword mutli-fields you want to have a full-text search in this field, and use it for sorting ([ES docs on multi-fields](https://www.elastic.co/guide/en/elasticsearch/reference/current/multi-fields.html)). This is unnecessary and inefficient for some fields that only need an equality check, and not the full-text search. For instance, such fields as identifier, url, license_version only need to be keywords, and they are never used in full-text search. 

To improve the mappings, in [#684](https://github.com/WordPress/openverse-api/pull/684) we did the following:
- set the mapping to static
- review the mappings to remove mapping for the fields that are not used in search. We can use `_source` property to get the values for the search result.
- remove multi-fields where they are absolutely not necessary.
