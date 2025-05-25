package com.bioinformatics.bioinformatics.model;

import java.util.*;

public class Search {
    private final List<String> mirnaNames;
    private final List<String> tools;
    private final String toolSelection;
    private final String heuristic;

    public Search(String[] mirnaNames, String[] tools, String toolSelection, String heuristic) {
        this.mirnaNames = Arrays.asList(mirnaNames);
        this.tools = Arrays.asList(tools);
        this.toolSelection = toolSelection;
        this.heuristic = heuristic;
    }

    public List<String> getmirnaNames() {
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

    @Override
    public String toString() {
        return String.join("|", mirnaNames) + "|||" +
                String.join("|", tools) + "|||" +
                toolSelection + "|||" + heuristic;
    }

    public static Search parse(String str) {
        String[] tokens = str.split("\\|\\|\\|");
        if (tokens.length < 4) return null;
        return new Search(tokens[0].split("\\|"), tokens[1].split("\\|"), tokens[2], tokens[3]);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Search other = (Search) o;
        return new HashSet<>(mirnaNames).equals(new HashSet<>(other.mirnaNames)) &&
                new HashSet<>(tools).equals(new HashSet<>(other.tools)) &&
                Objects.equals(toolSelection, other.toolSelection) &&
                Objects.equals(heuristic, other.heuristic);
    }

    @Override
    public int hashCode() {
        return Objects.hash(new HashSet<>(mirnaNames), new HashSet<>(tools), toolSelection, heuristic);
    }
}
