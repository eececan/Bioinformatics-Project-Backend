package com.bioinformatics.bioinformatics.service;

import com.bioinformatics.bioinformatics.model.Connection;
import com.bioinformatics.bioinformatics.model.GenePredictionDTO; // Assuming this is your DTO name
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

    private final Neo4jClient neo4jClient;
    private final MiRNARepository miRNARepository;

    @Autowired
    public MiRNAService(Neo4jClient neo4jClient, MiRNARepository miRNARepository) {
        this.neo4jClient = neo4jClient;
        this.miRNARepository = miRNARepository;
    }

    public Prediction getPredictions(String[] mirnaNames, String[] tools, String toolSelection, String heuristic, Map<String, String> cutoffs) {

        long startTime = System.nanoTime();

        String mirtarbaseFilter = (cutoffs != null) ? cutoffs.get("cutoffs[miRTarBase]") : null;
        Double tarbaseCutoff = (cutoffs != null) ? parseNumericCutoff(cutoffs.get("cutoffs[TarBase]")) : null;
        Double pictarCutoff = (cutoffs != null) ? parseNumericCutoff(cutoffs.get("cutoffs[PicTar]")) : null;
        Double targetscanCutoff = (cutoffs != null) ? parseNumericCutoff(cutoffs.get("cutoffs[TargetScan]")) : null;

        List<GenePredictionDTO> rawPredictions = miRNARepository.getPredictions(
                List.of(mirnaNames),
                List.of(tools),
                toolSelection,
                heuristic,
                mirtarbaseFilter,
                tarbaseCutoff,
                pictarCutoff,
                targetscanCutoff
        );

        int geneCount;
        int pathwayCount = 0;

        ArrayList<Prediction.PredictionValues> predictionValues = new ArrayList<>();
        if (rawPredictions == null || rawPredictions.isEmpty()) {
            predictionValues = new ArrayList<>();
            geneCount = 0;
        } else {
            for (var predictionDTO : rawPredictions) {
                pathwayCount += predictionDTO.pathways().size();
                predictionValues.add(new Prediction.PredictionValues(predictionDTO.gene(), predictionDTO.tools().toArray(new String[0]), predictionDTO.pathways().toArray(new String[0]), predictionDTO.connections().toArray(new Connection[0])));
            }
            geneCount = predictionValues.size();
        }

        long durationInNanoSeconds = (System.nanoTime() - startTime);
        Prediction prediction = new Prediction(mirnaNames, predictionValues.toArray(Prediction.PredictionValues[]::new),
                durationToString(durationInNanoSeconds), geneCount, pathwayCount);

        System.out.println("Search Time: " + prediction.getSearchTime());
        return prediction;
    }

    private Double parseNumericCutoff(String value) {
        if (value == null || value.trim().isEmpty()) {
            return null;
        }
        try {
            String numericPart = value.replaceAll("[^\\d.-]", "");
            if (numericPart.isEmpty()) return null;
            return Double.parseDouble(numericPart);
        } catch (NumberFormatException e) {
            System.err.println("Could not parse numeric cutoff: " + value);
            return null;
        }
    }

    public List<Map<String, Object>> getPathwaysByGene(String geneName) {
        return miRNARepository.findPathwaysByGeneName(geneName);
    }

    public GraphDataDTO getGraphDataForMiRNAs(List<String> miRNANames, List<String> tools, String toolSelection, String heuristic, Map<String, String> cutoffs) {

        String cypherQuery = """ 
    MATCH (m:microRNA)
    WHERE m.name IN $miRNANames

    MATCH (m)-[r]->(t:Target)
    WHERE
    type(r) IN $tools
    AND (
    (type(r) = 'miRTarBase' AND ($mirtarbaseFilter IS NULL OR toLower(r.experiments) CONTAINS toLower($mirtarbaseFilter))) OR
            (type(r) = 'TarBase'    AND ($tarbaseCutoff IS NULL OR r.score > $tarbaseCutoff)) OR
            (type(r) = 'PicTar'     AND ($pictarCutoff IS NULL OR r.score > $pictarCutoff)) OR
            (type(r) = 'TargetScan' AND ($targetscanCutoff IS NULL OR r.pct_score > $targetscanCutoff)) OR
            (NOT type(r) IN ['miRTarBase', 'TarBase', 'PicTar', 'TargetScan'])
            )

    OPTIONAL MATCH (t)-[:PART_OF_PATHWAY]->(p:Pathway)

    WITH
    toLower(t.name) AS targetName,

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

    HEAD(COLLECT(DISTINCT t)) AS t_node

    WITH
            t_node,
            pathways,
            connections,
            predictingMiRNAs,
            foundTools,
    SIZE(predictingMiRNAs) AS foundCount,
    CASE
    WHEN toUpper($heuristic) = 'INTERSECTION' THEN SIZE($miRNANames)
    WHEN toUpper($heuristic) = 'MAJORITY' THEN FLOOR(SIZE($miRNANames)/2.0 + 1)
    ELSE 1
    END AS requiredCount,
    $toolSelection AS toolSelection,
    $tools as tools

    WHERE
            (
                    toUpper(toolSelection) = 'UNION'
    OR (toUpper(toolSelection) = 'INTERSECTION' AND size(foundTools) = size(tools))
    OR (toUpper(toolSelection) = 'AT_LEAST_TWO' AND size(foundTools) >= 2)
            )
    AND foundCount >= requiredCount

    RETURN t_node AS t, pathways, connections, predictingMiRNAs
    """;

        String mirtarbaseFilter = (cutoffs != null) ? cutoffs.get("cutoffs[miRTarBase]") : null;
        Double tarbaseCutoff = (cutoffs != null) ? parseNumericCutoff(cutoffs.get("cutoffs[TarBase]")) : null;
        Double pictarCutoff = (cutoffs != null) ? parseNumericCutoff(cutoffs.get("cutoffs[PicTar]")) : null;
        Double targetscanCutoff = (cutoffs != null) ? parseNumericCutoff(cutoffs.get("cutoffs[TargetScan]")) : null;

        Collection<Map<String, Object>> results = neo4jClient.query(cypherQuery)
                .bind(miRNANames).to("miRNANames")
                .bind(tools).to("tools")
                .bind(toolSelection).to("toolSelection")
                .bind(heuristic).to("heuristic")
                .bind(mirtarbaseFilter).to("mirtarbaseFilter")
                .bind(tarbaseCutoff).to("tarbaseCutoff")
                .bind(pictarCutoff).to("pictarCutoff")
                .bind(targetscanCutoff).to("targetscanCutoff")
                .fetch().all();

        Map<String, GraphNodeDTO> nodesMap = new HashMap<>();
        Map<String, GraphEdgeDTO> edgesMap = new HashMap<>();

        for (Map<String, Object> row : results) {
            Node targetNode = (Node) row.get("t");
            @SuppressWarnings("unchecked")
            List<Node> pathwayNodes = (List<Node>) row.get("pathways");
            @SuppressWarnings("unchecked")
            List<Node> mirnaNodes = (List<Node>) row.get("predictingMiRNAs");
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> connections = (List<Map<String, Object>>) row.get("connections");

            if (!nodesMap.containsKey(targetNode.elementId())) {
                nodesMap.put(targetNode.elementId(), new GraphNodeDTO(
                        targetNode.elementId(),
                        targetNode.get("name").asString(),
                        "Target",
                        targetNode.asMap()
                ));
            }

            for (Node mirnaNode : mirnaNodes) {
                if (mirnaNode == null) continue;
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
                if (pathwayNode == null) continue;
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
}