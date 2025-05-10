package com.bioinformatics.bioinformatics.repository;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA;
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
    MATCH (m:miRNA {name: $miRNAName})-[r:TARGETS]->(g:Gene)
    OPTIONAL MATCH (g)-[:PARTICIPATES_IN]->(p:Pathway)
    WITH
      g.name     AS gene,
      collect(DISTINCT r.tool)      AS tools,
      collect(DISTINCT p.name)      AS pathways
    RETURN gene, tools, pathways
    ORDER BY gene
    """)
    List<GenePredictionDTO> getPredictions(@Param("miRNAName") String miRNAName);

    @Query("""
    MATCH (g:Targets {name: $name})-[:PART_OF]->(p:Pathway)
    RETURN collect({id: p.id, name: p.name})
    """)
    List<Map<String, Object>> findPathwaysByGeneName(@Param("name") String name);


}
