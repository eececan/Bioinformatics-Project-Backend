package com.bioinformatics.bioinformatics.model;

import java.util.List;

public record GraphDataDTO(
        List<GraphNodeDTO> nodes,
        List<GraphEdgeDTO> relationships
) {}