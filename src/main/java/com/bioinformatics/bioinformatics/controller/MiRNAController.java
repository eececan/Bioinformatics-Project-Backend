package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class MiRNAController {
    @Autowired
    MiRNARepository repo;

    // Existing endpoint for miRNA lookup
    @GetMapping("/mirna")
    public List<MiRNA> getMiRNA(@RequestParam String name) {
        return repo.findByName(name);
    }

    // New endpoint for predictions
    @GetMapping("/mirna/predictions")
    public ResponseEntity<Prediction> getPredictions(@RequestParam String name) {
        List<GenePredictionDTO> raw = repo.getPredictions(name);

        if (raw.isEmpty()) {
            return ResponseEntity.ok(new Prediction(name, new Prediction.PredictionValues[]{}));
        }

        List<Prediction.PredictionValues> vals = raw.stream()
                .map(p -> new Prediction.PredictionValues(
                        p.gene(),
                        p.tools().toArray(new String[0]),
                        p.pathways().toArray(new String[0])
                ))
                .toList();

        return ResponseEntity.ok(
                new Prediction(name, vals.toArray(new Prediction.PredictionValues[0]))
        );
    }

    @GetMapping("/gene/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam String name) {
        List<Map<String, Object>> result = repo.findPathwaysByGeneName(name);
        return ResponseEntity.ok(result);
    }




}