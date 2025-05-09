package com.bioinformatics.bioinformatics.model;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;

@Node("Pathway")
public class Pathway {

    @Id
    @Property("id")
    private String id;

    @Property("name")
    private String name;

    public Pathway() {}

    public Pathway(String id, String name) {
        this.id = id;
        this.name = name;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }
}
