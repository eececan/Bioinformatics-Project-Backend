package com.bioinformatics.bioinformatics.repository;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA; // Keeping the model class name as MiRNA
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;

@Repository
public interface MiRNARepository extends Neo4jRepository<MiRNA, Long> {
    List<MiRNA> findByName(String name);

    @Query("""
    MATCH (m:microRNA)
    WHERE m.name IN $miRNANames
    
    MATCH (m)-[r]->(t:Target)
    WHERE type(r) IN $tools
    
    OPTIONAL MATCH (t)-[:PART_OF_PATHWAY]->(p:Pathway)
    
    WITH
      t,
      t.name AS gene,
      collect(DISTINCT type(r))      AS foundTools,
      collect(DISTINCT p.name)       AS pathways,
      collect(DISTINCT m.name)       AS mirnasWithPrediction
    
    WITH
      gene,
      foundTools,
      [path IN pathways WHERE path IS NOT NULL] AS pathways,  // Remove nulls
      mirnasWithPrediction,
      size(mirnasWithPrediction)            AS foundCount,
      CASE
        WHEN toUpper($heuristic) = 'INTERSECTION' THEN size($miRNANames)
        WHEN toUpper($heuristic) = 'MAJORITY'     THEN ceil(size($miRNANames) / 2.0)
        ELSE 0
      END                                    AS requiredCount
    
    WHERE
      (
        toUpper($toolSelection) = 'UNION'
        OR
        (toUpper($toolSelection) = 'INTERSECTION' AND size(foundTools) = size($tools))
        OR
        (toUpper($toolSelection) = 'AT_LEAST_TWO' AND size(foundTools) >= 2)
      )
      AND
      foundCount >= requiredCount
    
    RETURN
      gene,
      foundTools AS tools,
      pathways
    ORDER BY gene
    """)
    List<GenePredictionDTO> getPredictions(
            @Param("miRNANames")      List<String> miRNANames,
            @Param("tools")           List<String> tools,
            @Param("toolSelection")   String toolSelection,
            @Param("heuristic")       String heuristic
    );

    @Query("""
    MATCH (t:Target {name: $name})-[:PART_OF_PATHWAY]->(p:Pathway)
    RETURN collect({id: p.id, name: p.name})
    """)
    List<Map<String, Object>> findPathwaysByGeneName(@Param("name") String name);

    @Query("MATCH (t:Target) RETURN t.name AS symbol")
    List<String> getAllTargetSymbols();

}
