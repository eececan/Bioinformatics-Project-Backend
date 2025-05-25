package com.bioinformatics.bioinformatics.model;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

public class Search {
    private final String[] miRNANames;
    private final String[] tools;
    private final String toolSelection;
    private final String heuristic;

    public Search(String[] miRNANames, String[] tools, String toolSelection, String heuristic) {
        this.miRNANames = miRNANames;
        this.tools = tools;
        this.toolSelection = toolSelection;
        this.heuristic = heuristic;
    }

    public String getHeuristic() {
        return heuristic;
    }

    public String getToolSelection() {
        return toolSelection;
    }

    public String[] getMiRNANames() {
        return miRNANames;
    }

    public String[] getTools() {
        return tools;
    }

    public String toString() {
        return String.join("|", miRNANames) + "|||" +
                String.join("|", tools) + "|||" +
                toolSelection + "|||" + heuristic;
    }

    public static Search parse(String str) {
        String[] tokens = str.split("\\|\\|\\|");
        return new Search(tokens[0].split("\\|"), tokens[1].split("\\|"), tokens[2], tokens[3]);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Search other = (Search) o;

        Set<String> thisMiRNAs = miRNANames != null ? new HashSet<>(Arrays.asList(miRNANames)) : null;
        Set<String> otherMiRNAs = other.miRNANames != null ? new HashSet<>(Arrays.asList(other.miRNANames)) : null;
        if (!Objects.equals(thisMiRNAs, otherMiRNAs)) return false;

        Set<String> thisTools = tools != null ? new HashSet<>(Arrays.asList(tools)) : null;
        Set<String> otherTools = other.tools != null ? new HashSet<>(Arrays.asList(other.tools)) : null;
        if (!Objects.equals(thisTools, otherTools)) return false;

        return Objects.equals(toolSelection, other.toolSelection)
                && Objects.equals(heuristic, other.heuristic);
    }

    @Override
    public int hashCode() {
        Set<String> miRNASet = miRNANames != null ? new HashSet<>(Arrays.asList(miRNANames)) : null;
        Set<String> toolSet = tools != null ? new HashSet<>(Arrays.asList(tools)) : null;
        return Objects.hash(miRNASet, toolSet, toolSelection, heuristic);
    }
}
