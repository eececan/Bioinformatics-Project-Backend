package com.bioinformatics.bioinformatics.model;

import java.util.*;
import java.util.stream.Collectors;

public class Search {
    private final List<String> mirnaNames;
    private final List<String> tools;
    private final String toolSelection;
    private final String heuristic;
    private final Map<String, String> cutoffs;

    public Search(String[] mirnaNames, String[] tools, String toolSelection, String heuristic, Map<String, String> cutoffs) {
        this.mirnaNames = Arrays.asList(mirnaNames);
        this.tools = Arrays.asList(tools);
        this.toolSelection = toolSelection;
        this.heuristic = heuristic;
        this.cutoffs = (cutoffs != null) ? Collections.unmodifiableMap(new HashMap<>(cutoffs)) : Collections.emptyMap();
    }

    private Search(String[] mirnaNames, String[] tools, String toolSelection, String heuristic) {
        this(mirnaNames, tools, toolSelection, heuristic, null);
    }

    public List<String> getMirnaNames() {
        return mirnaNames;
    }

    public List<String> getTools() {
        return tools;
    }

    public String getToolSelection() {
        return toolSelection;
    }

    public String getHeuristic() {
        return heuristic;
    }

    public Map<String, String> getCutoffs() {
        return cutoffs;
    }

    @Override
    public String toString() {
        String cutoffsString = this.cutoffs.entrySet().stream()
                .map(entry -> entry.getKey() + ":" + entry.getValue())
                .collect(Collectors.joining(";"));

        return String.join("|", mirnaNames) + "|||" +
                String.join("|", tools) + "|||" +
                toolSelection + "|||" +
                heuristic + "|||" +
                cutoffsString;
    }

    public static Search parse(String str) {
        if (str == null || str.isEmpty()) return null;

        String[] tokens = str.split("\\|\\|\\|");
        if (tokens.length < 4) return null; // Invalid format

        String[] mirnas = tokens[0].isEmpty() ? new String[0] : tokens[0].split("\\|");
        String[] tools = tokens[1].isEmpty() ? new String[0] : tokens[1].split("\\|");
        String toolSelection = tokens[2];
        String heuristic = tokens[3];

        Map<String, String> cutoffs = new HashMap<>();
        // Check if the cutoffs part exists (for backward compatibility)
        if (tokens.length > 4 && !tokens[4].isEmpty()) {
            String[] pairs = tokens[4].split(";");
            for (String pair : pairs) {
                // Split only on the first colon to allow colons in filter values
                String[] kv = pair.split(":", 2);
                if (kv.length == 2) {
                    cutoffs.put(kv[0], kv[1]);
                }
            }
        }

        return new Search(mirnas, tools, toolSelection, heuristic, cutoffs);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Search other = (Search) o;
        return new HashSet<>(mirnaNames).equals(new HashSet<>(other.mirnaNames)) &&
                new HashSet<>(tools).equals(new HashSet<>(other.tools)) &&
                Objects.equals(toolSelection, other.toolSelection) &&
                Objects.equals(heuristic, other.heuristic) &&
                Objects.equals(cutoffs, other.cutoffs);
    }

    @Override
    public int hashCode() {
        return Objects.hash(new HashSet<>(mirnaNames), new HashSet<>(tools), toolSelection, heuristic, cutoffs);
    }
}