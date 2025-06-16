package com.bioinformatics.bioinformatics.service;

import com.bioinformatics.bioinformatics.model.Connection;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.data.neo4j.core.Neo4jClient;
import com.bioinformatics.bioinformatics.model.GraphDataDTO;
import com.bioinformatics.bioinformatics.model.GraphEdgeDTO;
import com.bioinformatics.bioinformatics.model.GraphNodeDTO;
import org.neo4j.driver.types.Node;
import java.util.*;
import java.util.stream.Collectors;


@Service
public class MiRNAService {

    @Autowired
    private final Neo4jClient neo4jClient;

    @Autowired
    private final MiRNARepository miRNARepository;

    public MiRNAService(Neo4jClient neo4jClient, MiRNARepository miRNARepository) {
        this.neo4jClient = neo4jClient;
        this.miRNARepository = miRNARepository;
    }

    public Prediction getPredictions(String[] mirnaNames, String[] tools, String toolSelection, String heuristic) {

        long startTime = System.nanoTime();
        var rawPredictions = miRNARepository.getPredictions(
                List.of(mirnaNames),
                List.of(tools),
                toolSelection,
                heuristic);

        int geneCount;
        int pathwayCount = 0;

        ArrayList<Prediction.PredictionValues> predictionValues = new ArrayList<>();
        if(rawPredictions==null || rawPredictions.isEmpty())
        {
            predictionValues = new ArrayList<>();
            geneCount = 0;
        }
        else
        {
            for(var predictionDTO : rawPredictions) {
                pathwayCount += predictionDTO.pathways().size();
                predictionValues.add(new Prediction.PredictionValues(predictionDTO.gene(), predictionDTO.tools().toArray(new String[0]), predictionDTO.pathways().toArray(new String[0]), predictionDTO.connections().toArray(new Connection[0])));
            }
            geneCount = predictionValues.size();
        }

        long durationInNanoSeconds = (System.nanoTime() - startTime);

        Prediction prediction = new Prediction(mirnaNames, predictionValues.toArray(Prediction.PredictionValues[]::new),
                durationToString(durationInNanoSeconds), geneCount, pathwayCount);

        System.out.println(prediction.getSearchTime());

        return prediction;
    }

    private String durationToString(long durationInNanoSeconds) {
        double actualDuration;
        String durationUnit;

        if (durationInNanoSeconds <= 0) {
            return "0 ns";
        }

        int exponent = (int) Math.floor(Math.log10(durationInNanoSeconds));

        if (exponent > 5) {
            actualDuration = durationInNanoSeconds / 1000000000d;
            durationUnit = "s";

            if (actualDuration >= 60) {
                int actualDurationFloor = (int) Math.floor(actualDuration);
                return actualDurationFloor / 60 + " min " + (actualDurationFloor%60 == 0 ? "": actualDurationFloor % 60 + " s");
            }
        } else if (exponent > 2) {
            actualDuration = durationInNanoSeconds / 1000000d;
            durationUnit = "ms";
        } else if (exponent > 0) {
            actualDuration = durationInNanoSeconds / 1000d;
            durationUnit = "μs";
        } else {
            actualDuration = durationInNanoSeconds;
            durationUnit = "ns";
        }

        return (Math.round(actualDuration * 1000) / 1000d) + " " + durationUnit;
    }

    public List<Map<String, Object>> getPathwaysByGene(String geneName) {
        return miRNARepository.findPathwaysByGeneName(geneName);
    }

    public GraphDataDTO getGraphDataForMiRNAs(List<String> miRNANames, List<String> tools, String toolSelection, String heuristic) {

        String cypherQuery = """
            MATCH (m:microRNA)
            WHERE m.name IN $miRNANames
            
            MATCH (m)-[r]->(t:Target)
            WHERE size($tools) = 0 OR type(r) IN $tools
            
            OPTIONAL MATCH (t)-[:PART_OF_PATHWAY]->(p:Pathway)

            WITH
              t,
              COLLECT(DISTINCT type(r)) AS foundTools,
              COLLECT(DISTINCT p) AS pathways,
              COLLECT(DISTINCT {
                tool: type(r),
                quality: CASE
                  WHEN r.experiments IS NOT NULL THEN toString(r.experiments)
                  WHEN r.pct_score IS NOT NULL THEN toString(r.pct_score)
                  ELSE toString(r.score)
                END,
                mirna: m.name
              }) AS connections,
              COLLECT(DISTINCT m) AS predictingMiRNAs,
              SIZE(COLLECT(DISTINCT m)) AS foundCount,
              CASE
                WHEN toUpper($heuristic) = 'INTERSECTION' THEN SIZE($miRNANames)
                WHEN toUpper($heuristic) = 'MAJORITY' THEN FLOOR(SIZE($miRNANames)/2.0 + 1)
                ELSE 1
              END AS requiredCount

            WHERE
              (
                toUpper($toolSelection) = 'UNION'
                OR (toUpper($toolSelection) = 'INTERSECTION' AND size(foundTools) = size($tools))
                OR (toUpper($toolSelection) = 'AT_LEAST_TWO' AND size(foundTools) >= 2)
              )
              AND foundCount >= requiredCount

            RETURN t, pathways, connections, predictingMiRNAs
            """;

        Collection<Map<String, Object>> results = neo4jClient.query(cypherQuery)
                .bind(miRNANames).to("miRNANames")
                .bind(tools).to("tools")
                .bind(toolSelection).to("toolSelection")
                .bind(heuristic).to("heuristic")
                .fetch().all();

        Map<String, GraphNodeDTO> nodesMap = new HashMap<>();
        Map<String, GraphEdgeDTO> edgesMap = new HashMap<>();

        for (Map<String, Object> row : results) {
            // --- THE FINAL, FINAL FIX ---
            // The map contains the direct types. Cast them directly.
            Node targetNode = (Node) row.get("t");

            // The framework converts collections to standard Java Lists.
            @SuppressWarnings("unchecked")
            List<Node> pathwayNodes = (List<Node>) row.get("pathways");
            @SuppressWarnings("unchecked")
            List<Node> mirnaNodes = (List<Node>) row.get("predictingMiRNAs");
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> connections = (List<Map<String, Object>>) row.get("connections");

            // The rest of the logic remains unchanged.
            if (!nodesMap.containsKey(targetNode.elementId())) {
                nodesMap.put(targetNode.elementId(), new GraphNodeDTO(
                        targetNode.elementId(),
                        targetNode.get("name").asString(),
                        "Target",
                        targetNode.asMap()
                ));
            }

            for (Node mirnaNode : mirnaNodes) {
                if (mirnaNode == null) continue; // Safety check
                if (!nodesMap.containsKey(mirnaNode.elementId())) {
                    nodesMap.put(mirnaNode.elementId(), new GraphNodeDTO(
                            mirnaNode.elementId(),
                            mirnaNode.get("name").asString(),
                            "microRNA",
                            mirnaNode.asMap()
                    ));
                }
                String edgeId = "mirtarget-" + mirnaNode.elementId() + "-" + targetNode.elementId();
                if (!edgesMap.containsKey(edgeId)) {
                    String toolLabels = connections.stream()
                            .filter(conn -> conn.get("mirna").toString().equals(mirnaNode.get("name").asString()))
                            .map(conn -> String.format("%s (%s)", conn.get("tool"), conn.get("quality")))
                            .sorted()
                            .collect(Collectors.joining(", "));

                    edgesMap.put(edgeId, new GraphEdgeDTO(
                            edgeId,
                            mirnaNode.elementId(),
                            targetNode.elementId(),
                            toolLabels
                    ));
                }
            }

            for (Node pathwayNode : pathwayNodes) {
                if (pathwayNode == null) continue; // Safety check
                if (!nodesMap.containsKey(pathwayNode.elementId())) {
                    nodesMap.put(pathwayNode.elementId(), new GraphNodeDTO(
                            pathwayNode.elementId(),
                            pathwayNode.get("name").asString(),
                            "Pathway",
                            pathwayNode.asMap()
                    ));
                }
                String edgeId = "targetpath-" + targetNode.elementId() + "-" + pathwayNode.elementId();
                if (!edgesMap.containsKey(edgeId)) {
                    edgesMap.put(edgeId, new GraphEdgeDTO(
                            edgeId,
                            targetNode.elementId(),
                            pathwayNode.elementId(),
                            "PART_OF_PATHWAY"
                    ));
                }
            }
        }

        return new GraphDataDTO(new ArrayList<>(nodesMap.values()), new ArrayList<>(edgesMap.values()));
    }

}

