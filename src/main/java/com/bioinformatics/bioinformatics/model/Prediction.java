package com.bioinformatics.bioinformatics.model;


public class Prediction {
    private String[] mirna;
    private PredictionValues[] predictions;
    private String searchTime;
    private int geneCount;
    private int pathwayCount;

    public Prediction(String[] miRna, PredictionValues[] predictions, String searchTime, int geneCount, int pathwayCount) {
        this.mirna = miRna;
        this.predictions = predictions;
        this.searchTime = searchTime;
        this.geneCount = geneCount;
        this.pathwayCount = pathwayCount;
    }

    public Prediction() {}

    public PredictionValues[] getPredictions() {
        return predictions;
    }

    public String[] getMirna() {
        return mirna;
    }

    public String getSearchTime() {
        return searchTime;
    }

    public int getGeneCount() {
        return geneCount;
    }

    public int getPathwayCount() {
        return pathwayCount;
    }

    public void setPredictions(PredictionValues[] predictions) {
        this.predictions = predictions;
    }

    public void setMirna(String[] mirna) {
        this.mirna = mirna;
    }

    public void setSearchTime(String searchTime) {
        this.searchTime = searchTime;
    }

    public void setGeneCount(int geneCount) {
        this.geneCount = geneCount;
    }

    public void setPathwayCount(int pathwayCount) {
        this.pathwayCount = pathwayCount;
    }

    public static class PredictionValues
    {
        private String gene;
        private String[] tools;
        private String[] pathways;
        private Connection[] connections;

        public PredictionValues(String gene, String[] tools, String[] pathways, Connection[] connections)
        {
            this.gene = gene;
            this.tools = tools;
            this.pathways = pathways;
            this.connections = connections;
        }

        public PredictionValues() {}

        public String getGene() {
            return gene;
        }

        public String[] getTools() {
            return tools;
        }

        public String[] getPathways() {
            return pathways;
        }

        public Connection[] getConnections() {
            return connections;
        }
    }
}
