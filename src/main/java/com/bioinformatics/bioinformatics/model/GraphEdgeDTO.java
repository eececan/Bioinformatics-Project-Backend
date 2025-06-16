package com.bioinformatics.bioinformatics.model;

public record GraphEdgeDTO(
        String id,
        String source,
        String target,
        String label
) {}