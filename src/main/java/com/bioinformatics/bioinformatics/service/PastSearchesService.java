package com.bioinformatics.bioinformatics.service;

import com.bioinformatics.bioinformatics.model.Search;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class PastSearchesService {
    private static final Path SEARCH_LOG = Paths.get("previous_searches.txt");
    private static final int MAX_SEARCH_RESULTS = 10;

    private final LinkedList<Search> searches = init();

    public synchronized LinkedList<Search> init() {
        try
        {
            if (Files.notExists(SEARCH_LOG)) {
                Files.createFile(SEARCH_LOG);
            }
        }
        catch (IOException ignored) {}

        var ps = readPastSearchesFromFile();
        return new LinkedList<>(ps==null ? new ArrayList<>() : ps);
    }

    @Async("saveSearchAsync")
    public void saveSearchAsync(Search search) {
        try
        {
            saveSearch(search);
        }
        catch (IOException ignored) {}
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

    public List<Search> getPastSearches() {
        return searches == null ? readPastSearchesFromFile(): new ArrayList<>(searches);
    }

    private synchronized List<Search> readPastSearchesFromFile()
    {
        try
        {
            List<String> lines = Files.readAllLines(SEARCH_LOG, StandardCharsets.UTF_8);

            return lines.stream()
                    .map(Search::parse)
                    .collect(Collectors.toList());
        }
        catch (Exception e)
        {
            return new ArrayList<>();
        }
    }
}
