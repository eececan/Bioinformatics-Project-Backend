package com.bioinformatics.bioinformatics.model;

import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;

@Node("Pathway")
public class Pathway {

    @Id
    @GeneratedValue
    private Long id;
    private String name;

    public Pathway() {}
    public Pathway(String name, String id) {}
    public String getName() { return this.name; }
    public void setName(String name) {}
    public Long getId() { return this.id; }
    public void setId(Long id) {}
}
