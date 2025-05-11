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
MATCH (m:microRNA {name: $miRNAName})-[r]->(t:Target)
WHERE type(r) IN ['RNA22', 'PicTar', 'miRTarBase', 'TargetScan']
MATCH (t)-[:PART_OF_PATHWAY]->(p:Pathway)
WITH
  t.name AS gene,
  collect(DISTINCT type(r)) AS tools,
  collect(DISTINCT p.name) AS pathways
RETURN gene, tools, pathways
ORDER BY gene
""")
    List<GenePredictionDTO> getPredictions(@Param("miRNAName") String miRNAName);

    @Query("""
    MATCH (t:Target {name: $name})-[:PART_OF_PATHWAY]->(p:Pathway)
    RETURN collect({id: p.id, name: p.name})
    """)
    List<Map<String, Object>> findPathwaysByGeneName(@Param("name") String name);

    @Query("MATCH (t:Target) RETURN t.name AS symbol")
    List<String> getAllTargetSymbols();

}
