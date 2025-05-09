package com.bioinformatics.bioinformatics.model;

import com.bioinformatics.bioinformatics.Tool;
import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Target") // Map to Neo4j "Target" nodes
public class Gene {
    @Id @GeneratedValue private Long id;
    private String gene; // Maps to Target node's "name" property
    private Tool tool;
    private Double score;

    public Gene(){}

    public Gene(Long id, String gene,Tool tool,Double score){
        this.id = id;
        this.gene = gene;
        this.tool = tool;
        this.score = score;
    }

    public Double getScore() {
        return score;
    }

    public Long getId() {
        return id;
    }

    public String getGene() {
        return gene;
    }

    public Tool getTool() {
        return tool;
    }
}