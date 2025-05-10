package com.bioinformatics.bioinformatics;


import com.bioinformatics.bioinformatics.controller.MiRNAController;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class PredictionLogger implements CommandLineRunner {

    private final MiRNAController cont;

    public PredictionLogger(MiRNAController repo) {
        this.cont = repo;
    }

    @Override
    public void run(String... args) throws Exception {
        String miRNAName = (args.length > 0)? args[0] : "hsa-miR-155-5p";
        var a = cont.getPredictions(miRNAName);
        System.out.println(a);

    }
}