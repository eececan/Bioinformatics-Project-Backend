package com.bioinformatics.bioinformatics.repository;

import com.bioinformatics.bioinformatics.model.MiRNA;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface MiRNARepository extends Neo4jRepository<MiRNA, Long> {
    List<MiRNA> findByName(String name);
}
