package com.bioinformatics.bioinformatics;


import com.bioinformatics.bioinformatics.controller.MiRNAController;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(MiRNAController.class)
class MiRNAControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private MiRNARepository repo;

    @Test
    @DisplayName("GET /api/mirna/predictions?name=miR-1 → 200 + correct JSON")
    void whenValidMiRName_thenReturnPredictions() throws Exception {
        // — given
        Map<String, Object> mockResult = Map.of(
                "predictions", List.of(
                        Map.of("gene", "TP53",  "tool", "RNA22",      "score", 0.85),
                        Map.of("gene", "BRCA1", "tool", "TargetScan", "score", 0.92)
                )
        );
        given(repo.getPredictions("miR-1")).willReturn(mockResult);

        // — when / then
        mockMvc.perform( get("/api/mirna/predictions").param("name", "miR-1")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].gene").value("TP53"))
                .andExpect(jsonPath("$[0].tool").value("RNA22"))
                .andExpect(jsonPath("$[0].score").value(0.85))
                .andExpect(jsonPath("$[1].gene").value("BRCA1"))
                .andExpect(jsonPath("$[1].tool").value("TargetScan"))
                .andExpect(jsonPath("$[1].score").value(0.92));

    }
}