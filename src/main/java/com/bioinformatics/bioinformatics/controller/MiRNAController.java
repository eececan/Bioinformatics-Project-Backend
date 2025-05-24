package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.Arrays;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class MiRNAController {
    @Autowired
    private final MiRNARepository miRNARepository;

    public MiRNAController(MiRNARepository miRNARepository) {
        this.miRNARepository = miRNARepository;
    }

    @GetMapping
    public ResponseEntity<List<MiRNA>> getByName(@RequestParam("name") String name) {
        return ResponseEntity.ok(miRNARepository.findByName(name));
    }


    /**
     * @param miRNANames List of microRNA names to query.
     * @param tools List of tool relationship types to consider.
     * @param toolSelection Strategy to filter predictions based on tools (UNION, INTERSECTION, AT_LEAST_TWO).
     * @param heuristic Heuristic for minimum number of miRNAs predicting a gene (INTERSECTION, MAJORITY).
     * @return A list of gene predictions including gene name, tools that predicted it, and related pathways.
     */
    @GetMapping("/predictions")
    public ResponseEntity<Prediction> getPredictions(@RequestParam("miRNANames") String[] miRNANames, @RequestParam("tools") String[] tools, @RequestParam("toolSelection") String toolSelection, @RequestParam("heuristic") String heuristic) {
        return ResponseEntity.ok(buildPrediction(miRNANames, miRNARepository.getPredictions(Arrays.asList(miRNANames), Arrays.asList(tools), toolSelection, heuristic)));
    }



    @GetMapping("/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam("geneName") String geneName) {
        List<Map<String, Object>> pathways = miRNARepository.findPathwaysByGeneName(geneName);
        return ResponseEntity.ok(pathways);
    }

    private Prediction buildPrediction(String[] names, List<GenePredictionDTO> rawPredictions) {
        if (rawPredictions == null || rawPredictions.isEmpty()) {
            return new Prediction(names, new Prediction.PredictionValues[0]);
        }

        return new Prediction(names, rawPredictions.stream()
                .map(dto -> new Prediction.PredictionValues(
                        dto.gene(),
                        dto.tools().toArray(new String[0]),
                        dto.pathways().toArray(new String[0])
                )).toArray(Prediction.PredictionValues[]::new));
    }


}