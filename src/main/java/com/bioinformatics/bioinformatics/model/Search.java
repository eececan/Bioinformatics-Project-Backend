package com.bioinformatics.bioinformatics.model;

public class Search {
    private String[] miRNANames;
    private String[] tools;
    private String toolSelection;
    private String heuristic;

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
}
