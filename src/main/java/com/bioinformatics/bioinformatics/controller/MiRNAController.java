package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.model.Search;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import com.bioinformatics.bioinformatics.service.PastSearchesService;
import jakarta.annotation.PostConstruct;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Async;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api")
public class MiRNAController {

    @Autowired
    private MiRNARepository miRNARepository;

    @Autowired
    private PastSearchesService pastSearchesService;



    /**
     * @param miRNANames List of microRNA names to query.
     * @param tools List of tool relationship types to consider.
     * @param toolSelection Strategy to filter predictions based on tools (UNION, INTERSECTION, AT_LEAST_TWO).
     * @param heuristic Heuristic for minimum number of miRNAs predicting a gene (INTERSECTION, MAJORITY).
     * @return A list of gene predictions including gene name, tools that predicted it, and related pathways.
     */
    @GetMapping("/predictions")
    public ResponseEntity<Prediction> getPredictions(
            @RequestParam("miRNANames") String[] miRNANames,
            @RequestParam("tools") String[] tools,
            @RequestParam("toolSelection") String toolSelection,
            @RequestParam("heuristic") String heuristic) throws IOException {

        long startTime = System.nanoTime();
        var rawPredictions = miRNARepository.getPredictions(
                                            List.of(miRNANames),
                                            List.of(tools),
                                            toolSelection,
                                            heuristic);

        int geneCount;
        int pathwayCount = 0;

        ArrayList<Prediction.PredictionValues> predictionValues = new ArrayList<>();
        if(rawPredictions==null || rawPredictions.isEmpty())
        {
            predictionValues = new ArrayList<>();
            geneCount = 0;
        }
        else
        {
            for(var predictionDTO : rawPredictions) {
                pathwayCount += predictionDTO.pathways().size();
                predictionValues.add(new Prediction.PredictionValues(predictionDTO.gene(), predictionDTO.tools().toArray(new String[0]), predictionDTO.pathways().toArray(new String[0])));
            }
            geneCount = predictionValues.size();
        }

        double durationInSeconds = (System.nanoTime() - startTime) / 1_000_000_000.0;

        Prediction prediction = new Prediction(miRNANames, predictionValues.toArray(Prediction.PredictionValues[]::new), durationInSeconds, geneCount, pathwayCount);

        pastSearchesService.saveSearchAsync(new Search(miRNANames, tools, toolSelection, heuristic));

        return ResponseEntity.ok(prediction);
    }



    @GetMapping("/pastSearches")
    public synchronized ResponseEntity<List<Search>> getPastSearches() {
        return ResponseEntity.ok(pastSearchesService.getPastSearches());
    }



    @GetMapping("/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam("geneName") String geneName) {
        List<Map<String, Object>> pathways = miRNARepository.findPathwaysByGeneName(geneName);
        return ResponseEntity.ok(pathways);
    }

}