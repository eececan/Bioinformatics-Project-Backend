package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.Tool;
import com.bioinformatics.bioinformatics.model.Gene;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.model.Pathway;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

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
    public ResponseEntity<List<Gene>> getPredictions(@RequestParam String name) {
        List<Map<String, Object>> predictions = repo.getPredictions(name);

        if (predictions == null || predictions.isEmpty()) {
            return ResponseEntity.ok(new ArrayList<>());
        }

        List<Gene> result = new ArrayList<>();
        for (Map<String, Object> p : predictions) {
            result.add(new Gene(
                    null,
                    (String) p.get("gene"),
                    Tool.valueOf((String) p.get("tool")),
                    Double.parseDouble((String) p.get("score"))

            ));
        }

        return ResponseEntity.ok(result);
    }

    @GetMapping("/gene/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam String name) {
        List<Map<String, Object>> result = repo.findPathwaysByGeneName(name);
        return ResponseEntity.ok(result);
    }


}