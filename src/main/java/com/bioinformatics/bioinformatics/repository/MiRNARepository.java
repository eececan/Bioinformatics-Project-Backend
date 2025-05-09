package com.bioinformatics.bioinformatics.repository;

import com.bioinformatics.bioinformatics.model.Gene;
import com.bioinformatics.bioinformatics.model.MiRNA;
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
    MATCH (m:MiRNA)-[r]->(t:Target)
    WHERE m.name = $name AND type(r) IN ['RNA22', 'TargetScan', 'PicTar', 'miRTarBase']
    RETURN m.name AS mirna, collect({gene: t.name, tool: type(r), score: r.score}) AS predictions
    """)
    Map<String, Object> getPredictions(@Param("name") String name);
}
