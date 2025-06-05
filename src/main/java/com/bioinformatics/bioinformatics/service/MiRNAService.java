package com.bioinformatics.bioinformatics.service;

import com.bioinformatics.bioinformatics.model.Connection;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class MiRNAService {
    @Autowired
    private MiRNARepository miRNARepository;

    public Prediction getPredictions(String[] mirnaNames, String[] tools, String toolSelection, String heuristic) {

        long startTime = System.nanoTime();
        var rawPredictions = miRNARepository.getPredictions(
                List.of(mirnaNames),
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
                predictionValues.add(new Prediction.PredictionValues(predictionDTO.gene(), predictionDTO.tools().toArray(new String[0]), predictionDTO.pathways().toArray(new String[0]), predictionDTO.connections().toArray(new Connection[0])));
            }
            geneCount = predictionValues.size();
        }

        long durationInNanoSeconds = (System.nanoTime() - startTime);

        Prediction prediction = new Prediction(mirnaNames, predictionValues.toArray(Prediction.PredictionValues[]::new),
                durationToString(durationInNanoSeconds), geneCount, pathwayCount);

        System.out.println(prediction.getSearchTime());

        return prediction;
    }

    private String durationToString(long durationInNanoSeconds) {
        double actualDuration;
        String durationUnit;

        if (durationInNanoSeconds <= 0) {
            return "0 ns";
        }

        int exponent = (int) Math.floor(Math.log10(durationInNanoSeconds));

        if (exponent > 5) {
            actualDuration = durationInNanoSeconds / 1000000000d;
            durationUnit = "s";

            if (actualDuration >= 60) {
                int actualDurationFloor = (int) Math.floor(actualDuration);
                return actualDurationFloor / 60 + " min " + (actualDurationFloor%60 == 0 ? "": actualDurationFloor % 60 + " s");
            }
        } else if (exponent > 2) {
            actualDuration = durationInNanoSeconds / 1000000d;
            durationUnit = "ms";
        } else if (exponent > 0) {
            actualDuration = durationInNanoSeconds / 1000d;
            durationUnit = "μs";
        } else {
            actualDuration = durationInNanoSeconds;
            durationUnit = "ns";
        }

        return (Math.round(actualDuration * 1000) / 1000d) + " " + durationUnit;
    }

    public List<Map<String, Object>> getPathwaysByGene(String geneName) {
        return miRNARepository.findPathwaysByGeneName(geneName);
    }
}
