package com.bioinformatics.bioinformatics.model;

import java.util.List;

public record GenePredictionDTO(
        String gene,
        List<String> tools,
        List<String> pathways
) {}