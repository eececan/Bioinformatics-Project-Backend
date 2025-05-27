package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.model.Search;
import com.bioinformatics.bioinformatics.service.MiRNAService;
import com.bioinformatics.bioinformatics.service.PastSearchesService;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.*;

@RestController
@RequestMapping("/api")
public class MiRNAController {
    @Autowired
    private MiRNAService miRNAService;
    @Autowired
    private PastSearchesService pastSearchesService;

    /**
     * @param mirnaNames List of microRNA names to query.
     * @param tools List of tool relationship types to consider.
     * @param toolSelection Strategy to filter predictions based on tools (UNION, INTERSECTION, AT_LEAST_TWO).
     * @param heuristic Heuristic for minimum number of miRNAs predicting a gene (INTERSECTION, MAJORITY).
     * @return A list of gene predictions including gene name, tools that predicted it, and related pathways.
     */
    @GetMapping("/predictions")
    public ResponseEntity<Prediction> getPredictions(
            @RequestParam("mirnaNames") String[] mirnaNames,
            @RequestParam("tools") String[] tools,
            @RequestParam("toolSelection") String toolSelection,
            @RequestParam("heuristic") String heuristic) {

        pastSearchesService.saveSearchAsync(new Search(mirnaNames, tools, toolSelection, heuristic));
        return ResponseEntity.ok(miRNAService.getPredictions(mirnaNames, tools, toolSelection, heuristic));
    }

    @GetMapping("/pastSearches")
    public synchronized ResponseEntity<List<Search>> getPastSearches() {
        return ResponseEntity.ok(pastSearchesService.getPastSearches());
    }

    @GetMapping("/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam("geneName") String geneName) {
        return ResponseEntity.ok(miRNAService.getPathwaysByGene(geneName));
    }
}