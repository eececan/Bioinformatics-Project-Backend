**MiRNASearch Web Application**

**Overview**
This backend service provides a RESTful API for querying microRNA (miRNA) target genes and associated biological pathways. It aggregates predictions from PicTar, miRTarBase, TargetScan, and RNA22, stores the data in Neo4j, and exposes endpoints for flexible tool- and miRNA-based merge strategies.

**Key Features**

* Unified access to four miRNA–target prediction resources for *Mus musculus*.
* Customizable prefiltering parameters (see Appendix A).
* Graph-based data model using Neo4j to represent miRNAs, genes, interactions, and pathways.
* Heuristic merging strategies: union, intersection, at-least-two-tools, plus miRNA-level consensus (intersection/majority).
* Endpoint returns gene lists, pathway associations, tool scores or experimental evidence, and query execution time.
* History of past searches stored for quick re-query.

**Technologies & Frameworks**

* **Java**: Core language for backend logic.
* **Spring Boot**: Rapid setup of REST controllers and dependency injection.
* **Neo4j (v1.6.1)**: Graph database for relationship modeling.
* **KEGG REST API**: Dynamic retrieval of gene–pathway mappings.
