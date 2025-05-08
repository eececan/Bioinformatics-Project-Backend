package com.bioinformatics.bioinformatics.controller;
import com.bioinformatics.bioinformatics.model.MiRNA;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;


@RestController
@RequestMapping("/api")
public class MiRNAController {
    @Autowired
    MiRNARepository repo;

    @GetMapping("/mirna")
    public List<MiRNA> get(@RequestParam String name) {
        return repo.findByName(name);
    }
}
