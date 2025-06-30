package com.bioinformatics.bioinformatics.repository;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import org.springframework.lang.Nullable;
import java.util.List;
import java.util.Map;

@Repository
public interface MiRNARepository extends Neo4jRepository<MiRNA, Long> {
    List<MiRNA> findByName(String name);

    @Query("""
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
    t.name AS geneName,
    COLLECT(DISTINCT type(r)) AS foundTools,
    COLLECT(DISTINCT p.name) AS pathwayNames,
    COLLECT(DISTINCT {
        tool: type(r),
                quality: CASE
        WHEN r.experiments IS NOT NULL THEN toString(r.experiments)
                WHEN r.pct_score IS NOT NULL THEN toString(r.pct_score)
                ELSE toString(r.score)
        END,
                mirna: m.name
    }) AS connections,
    COLLECT(DISTINCT m.name) AS predictingMiRNANames

    WITH
            geneName,
            foundTools,
            pathwayNames,
            connections,
    SIZE(predictingMiRNANames) AS foundCount,
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

            RETURN
    geneName AS gene,
    foundTools AS tools,
    pathwayNames AS pathways,
    connections
    """)
    List<GenePredictionDTO> getPredictions(
            // Original parameters
            @Param("miRNANames")    List<String> miRNANames,
            @Param("tools")         List<String> tools,
            @Param("toolSelection") String       toolSelection,
            @Param("heuristic")     String       heuristic,

            @Param("mirtarbaseFilter") @Nullable String mirtarbaseFilter,
            @Param("tarbaseCutoff")    @Nullable Double tarbaseCutoff,
            @Param("pictarCutoff")     @Nullable Double pictarCutoff,
            @Param("targetscanCutoff") @Nullable Double targetscanCutoff
    );

    @Query("""
    MATCH (t:Target {name: $name})-[:PART_OF_PATHWAY]->(p:Pathway)
    RETURN collect({id: p.id, name: p.name})
    """)
    List<Map<String, Object>> findPathwaysByGeneName(@Param("name") String name);

    @Query("MATCH (t:Target) RETURN t.name AS symbol")
    List<String> getAllTargetSymbols();
}
