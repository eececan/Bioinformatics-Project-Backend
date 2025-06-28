package com.bioinformatics.bioinformatics.service;

import com.bioinformatics.bioinformatics.model.Search;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class PastSearchesService {
    private static final Logger log = LoggerFactory.getLogger(PastSearchesService.class);
    private static final Path SEARCH_LOG = Paths.get("previous_searches.txt");
    private static final int MAX_SEARCH_RESULTS = 10;

    private final List<Search> searches = Collections.synchronizedList(new LinkedList<>());

    @PostConstruct
    public void initialize() {
        try {
            if (Files.notExists(SEARCH_LOG)) {
                Files.createFile(SEARCH_LOG);
                log.info("Created new past searches log file at: {}", SEARCH_LOG.toAbsolutePath());
            }
            this.searches.clear();
            this.searches.addAll(readPastSearchesFromFile());
            log.info("Successfully loaded {} past searches from file.", this.searches.size());
        } catch (IOException e) {
            log.error("Failed to initialize or read past searches file.", e);
        }
    }

    @Async("saveSearchAsync")
    public void saveSearchAsync(Search search) {
        synchronized (this.searches) {
            try {
                searches.remove(search);

                searches.add(0, search);

                while (searches.size() > MAX_SEARCH_RESULTS) {
                    searches.remove(searches.size() - 1);
                }

                writeSearchesToFile();
            } catch (Exception e) {
                log.error("Failed to save search asynchronously.", e);
            }
        }
    }

    /**
     * Returns a copy of the past searches list.
     * The method is synchronized on the list to prevent reading while it's being modified.
     */
    public List<Search> getPastSearches() {
        synchronized (this.searches) {
            return new ArrayList<>(this.searches);
        }
    }

    private void writeSearchesToFile() throws IOException {
        List<String> lines = this.searches.stream()
                .map(Search::toString)
                .collect(Collectors.toList());

        Files.write(SEARCH_LOG, lines, StandardCharsets.UTF_8);
    }

    private List<Search> readPastSearchesFromFile() throws IOException {
        List<String> lines = Files.readAllLines(SEARCH_LOG, StandardCharsets.UTF_8);
        return lines.stream()
                .map(Search::parse)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }
}