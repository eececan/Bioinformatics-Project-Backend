package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.model.GraphDataDTO;
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

    private final MiRNAService miRNAService;
    private final PastSearchesService pastSearchesService;

    @Autowired
    public MiRNAController(MiRNAService miRNAService, PastSearchesService pastSearchesService) {
        this.miRNAService = miRNAService;
        this.pastSearchesService = pastSearchesService;
    }

    /**
     * @param mirnaNames List of microRNA names to query.
     * @param tools List of tool relationship types to consider.
     * @param toolSelection Strategy to filter predictions based on tools (UNION, INTERSECTION, AT_LEAST_TWO).
     * @param heuristic Heuristic for minimum number of miRNAs predicting a gene (INTERSECTION, MAJORITY).
     * @param cutoffs A map of tool-specific filters (e.g., "PicTar" -> "> 300").
     * @return A list of gene predictions including gene name, tools that predicted it, and related pathways.
     */

    @GetMapping("/predictions")
    public ResponseEntity<Prediction> getPredictions(
            @RequestParam("mirnaNames") String[] mirnaNames,
            @RequestParam("tools") String[] tools,
            @RequestParam("toolSelection") String toolSelection,
            @RequestParam("heuristic") String heuristic,
            @RequestParam(required = false) Map<String, String> cutoffs) {

        pastSearchesService.saveSearchAsync(new Search(mirnaNames, tools, toolSelection, heuristic, cutoffs));

        Prediction predictions = miRNAService.getPredictions(mirnaNames, tools, toolSelection, heuristic, cutoffs);
        return ResponseEntity.ok(predictions);
    }

    @GetMapping("/pastSearches")
    public synchronized ResponseEntity<List<Search>> getPastSearches() {
        return ResponseEntity.ok(pastSearchesService.getPastSearches());
    }

    @GetMapping("/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam("geneName") String geneName) {
        return ResponseEntity.ok(miRNAService.getPathwaysByGene(geneName));
    }

    @GetMapping("/graph")
    public ResponseEntity<GraphDataDTO> getGraphData(
            @RequestParam List<String> miRNANames,
            @RequestParam(required = false, defaultValue = "") List<String> tools,
            @RequestParam String toolSelection,
            @RequestParam String heuristic,
            @RequestParam(required = false) Map<String, String> cutoffs
    ) {
        if (tools.size() == 1 && tools.get(0).isEmpty()) {
            tools = Collections.emptyList();
        }

        GraphDataDTO graphData = miRNAService.getGraphDataForMiRNAs(miRNANames, tools, toolSelection, heuristic, cutoffs);
        return ResponseEntity.ok(graphData);
    }
}