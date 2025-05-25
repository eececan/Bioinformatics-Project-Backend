package com.bioinformatics.bioinformatics.controller;

import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.model.Search;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import jakarta.annotation.PostConstruct;
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
    private static final Path SEARCH_LOG = Paths.get("previous_searches.txt");
    private static final int MAX_SEARCH_RESULTS = 10;

    @Autowired
    private MiRNARepository miRNARepository;

    private final LinkedList<Search> searches = init();

    public synchronized LinkedList<Search> init() {
        try
        {
            if (Files.notExists(SEARCH_LOG)) {
                Files.createFile(SEARCH_LOG);
            }
        }
        catch (IOException ignored) {}

        var ps = getPastSearches();
        return new LinkedList<>(ps==null || ps.getBody() == null ? new ArrayList<>() : ps.getBody());
    }

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

        double durationInSeconds = (System.nanoTime() - startTime) / 1_000_000_000.0;

        var predictions = rawPredictions == null || rawPredictions.isEmpty() ? new Prediction(miRNANames, new Prediction.PredictionValues[0], durationInSeconds):
                                                new Prediction(miRNANames, rawPredictions.stream()
                                                .map(dto -> new Prediction.PredictionValues(
                                                        dto.gene(),
                                                        dto.tools().toArray(new String[0]),
                                                        dto.pathways().toArray(new String[0])
                                                )).toArray(Prediction.PredictionValues[]::new), durationInSeconds);

        try
        {
            saveSearch(new Search(miRNANames, tools, toolSelection, heuristic));
        }
        catch (IOException ignored) {}

        return ResponseEntity.ok(predictions);
    }

    private synchronized void saveSearch(Search search) throws IOException {
        searches.remove(search);

        searches.add(0, search);

        if(searches.size() > MAX_SEARCH_RESULTS) {
            searches.removeLast();
        }

        StringBuilder sb = new StringBuilder();

        for(Search s : searches) {
            sb.append(s.toString()).append(System.lineSeparator());
        }

        Files.writeString(SEARCH_LOG, sb.toString());
    }

    @GetMapping("/pastSearches")
    public ResponseEntity<List<Search>> getPastSearches() {
        try
        {
            List<String> lines = Files.readAllLines(SEARCH_LOG, StandardCharsets.UTF_8);
            List<Search> pastSearches = lines.stream()
                    .map(Search::parse)
                    .collect(Collectors.toList());

            return ResponseEntity.ok(pastSearches);
        }
        catch (IOException e)
        {
            return ResponseEntity.ok(new ArrayList<>());
        }

    }

    @GetMapping("/pathways")
    public ResponseEntity<List<Map<String, Object>>> getPathwaysByGene(@RequestParam("geneName") String geneName) {
        List<Map<String, Object>> pathways = miRNARepository.findPathwaysByGeneName(geneName);
        return ResponseEntity.ok(pathways);
    }

}