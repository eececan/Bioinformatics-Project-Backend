package com.bioinformatics.bioinformatics.model;

import java.util.Map;

public record GraphNodeDTO(
        String id,
        String label,
        String type,
        Map<String, Object> properties
) {}