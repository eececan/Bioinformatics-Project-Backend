package com.bioinformatics.bioinformatics.model;

import com.bioinformatics.bioinformatics.Tool;
import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Target")
public class Gene {
    @Id @GeneratedValue private Long id;
    private String name;
    private Tool tool;
    private Double score;

    public Gene() {}

    public Gene(Long id, String name, Tool tool, Double score) {
        this.id = id;
        this.name = name;
        this.tool = tool;
        this.score = score;
    }

    public Gene(String name, Tool tool, Double score) {
        this(null, name, tool, score);
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public Tool getTool() { return tool; }
    public Double getScore() { return score; }
}
