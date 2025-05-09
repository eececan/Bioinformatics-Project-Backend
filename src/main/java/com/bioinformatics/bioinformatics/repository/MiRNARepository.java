package com.bioinformatics.bioinformatics.repository;

import com.bioinformatics.bioinformatics.model.Gene;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.model.Pathway;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

@Repository
public interface MiRNARepository extends Neo4jRepository<MiRNA, Long> {
    List<MiRNA> findByName(String name);

    @Query("""
    MATCH (m:microRNA)-[r]->(t:Target)
    WHERE m.name = $name AND type(r) IN ['RNA22', 'TargetScan', 'PicTar', 'miRTarBase']
    RETURN collect({gene: t.name, tool: type(r), score: r.score})
""")
    List<Map<String, Object>> getPredictions(@Param("name") String name);

    @Query("""
    MATCH (g:Target {name: $name})-[:PART_OF]->(p:Pathway)
    RETURN collect({id: p.id, name: p.name})
""")
    List<Map<String, Object>> findPathwaysByGeneName(@Param("name") String name);


}
