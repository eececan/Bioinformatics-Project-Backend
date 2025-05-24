package com.bioinformatics.bioinformatics.model;


public class Prediction {
    private String[] mirna;
    private PredictionValues[] predictions;

    public Prediction(String[] miRna, PredictionValues[] predictions) {
        this.mirna = miRna;
        this.predictions = predictions;
    }

    public Prediction() {}

    public PredictionValues[] getPredictions() {
        return predictions;
    }

    public String[] getMirna() {
        return mirna;
    }

    public void setPredictions(PredictionValues[] predictions) {
        this.predictions = predictions;
    }

    public void setMirna(String[] mirna) {
        this.mirna = mirna;
    }

    public static class PredictionValues
    {
        private String gene;
        private String[] tools;
        private String[] pathways;

        public PredictionValues(String gene, String[] tools, String[] pathways)
        {
            this.gene = gene;
            this.tools = tools;
            this.pathways = pathways;
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
    }
}
