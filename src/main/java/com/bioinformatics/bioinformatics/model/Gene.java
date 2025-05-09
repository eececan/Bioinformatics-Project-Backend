package com.bioinformatics.bioinformatics.model;

import com.bioinformatics.bioinformatics.Tool;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Target") // Map to Neo4j "Target" nodes
@Getter @Setter
@AllArgsConstructor
public class Gene {
    @Id @GeneratedValue private Long id;
    private String name; // Maps to Target node's "name" property
    private Tool tool;
    private Double score;

    public Gene(){}
}