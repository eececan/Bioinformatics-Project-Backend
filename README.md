## MiRNASearch Web Application

**Overview**
This backend service provides a RESTful API for querying microRNA (miRNA) target genes and associated biological pathways. It aggregates predictions from PicTar, miRTarBase, TargetScan, and RNA22, stores the data in Neo4j, and exposes endpoints for flexible tool- and miRNA-based merge strategies.

**Key Features**

* Unified access to four miRNA–target prediction resources for *Mus musculus*.
* Customizable prefiltering parameters.
* Graph-based data model using Neo4j to represent miRNAs, genes, interactions, and pathways.
* Heuristic merging strategies: union, intersection, at-least-two-tools, plus miRNA-level consensus (intersection/majority).
* Endpoint returns gene lists, pathway associations, tool scores or experimental evidence, and query execution time.
* History of past searches stored for quick re-query.

**Technologies & Frameworks**

* **Java**: Core language for backend logic.
* **Spring Boot**: Rapid setup of REST controllers and dependency injection.
* **Neo4j (v1.6.1)**: Graph database for relationship modeling.
* **KEGG REST API**: Dynamic retrieval of gene–pathway mappings.

---

## REST Endpoints

### GET /predictions

Fetch gene predictions for a set of miRNAs, filtered by selected prediction tools and consensus heuristics.

**Parameters** (all passed as query parameters):

| Name            | Type      | Description                                                                                        |
| --------------- | --------- | -------------------------------------------------------------------------------------------------- |
| `mirnaNames`    | String\[] | List of microRNA names to query (e.g., `mmu-miR-21`, `mmu-let-7a`).                                |
| `tools`         | String\[] | Prediction resources to consider. Supported values: `PicTar`, `miRTarBase`, `TargetScan`, `RNA22`. |
| `toolSelection` | String    | Strategy to merge predictions across tools. Options:                                               |
|                 |           | - `UNION`: include any gene predicted by at least one tool.                                        |
|                 |           | - `INTERSECTION`: include only genes predicted by *all* selected tools.                            |
|                 |           | - `AT_LEAST_TWO`: include genes predicted by two or more of the selected tools.                    |
| `heuristic`     | String    | Consensus rule across miRNAs. Options:                                                             |
|                 |           | - `INTERSECTION`: require every queried miRNA to predict the returned gene.                        |
|                 |           | - `MAJORITY`: require more than half of the queried miRNAs to predict the returned gene.           |

**Response**:

Returns a JSON payload with the following structure:

```json
{
  "mirnas": ["mmu-miR-21", "mmu-let-7a"],
  "predictions": [
    {
      "gene": "GeneA",
      "tools": ["PicTar", "TargetScan"],
      "pathways": ["Apoptosis", "Cell Cycle"],
      "connections": [
        {
          "tool": "PicTar",
          "quality": "0.85",
          "mirna": "mmu-miR-21"
        },
        {
          "tool": "TargetScan",
          "quality": "3 experiments",
          "mirna": "mmu-let-7a"
        }
      ]
    }
  ],
  "searchTime": "50 ms",
  "geneCount": 1,
  "pathwayCount": 2
}
```

**Controller Method** (`getPredictions`):

```java
@GetMapping("/predictions")
public ResponseEntity<Prediction> getPredictions(
        @RequestParam("mirnaNames") String[] mirnaNames,
        @RequestParam("tools") String[] tools,
        @RequestParam("toolSelection") String toolSelection,
        @RequestParam("heuristic") String heuristic) {
    // Asynchronously save the search parameters
    pastSearchesService.saveSearchAsync(
        new Search(mirnaNames, tools, toolSelection, heuristic)
    );
    // Delegate to service layer and return results
    return ResponseEntity.ok(
        miRNAService.getPredictions(
            mirnaNames, tools, toolSelection, heuristic
        )
    );
}
```

* **Parameter Binding**: Maps HTTP query parameters to Java arrays and strings.
* **Search Logging**: Invokes `pastSearchesService.saveSearchAsync` for audit/history.
* **Service Delegation**: Calls `miRNAService.getPredictions` to perform graph query and assemble the `Prediction` object.

---

*End of Documentation.*
