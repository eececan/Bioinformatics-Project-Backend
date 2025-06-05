package com.bioinformatics.bioinformatics;

import com.bioinformatics.bioinformatics.controller.MiRNAController;
import com.bioinformatics.bioinformatics.model.Connection;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.model.Search;
import com.bioinformatics.bioinformatics.service.MiRNAService;
import com.bioinformatics.bioinformatics.service.PastSearchesService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Arrays;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;


@WebMvcTest(MiRNAController.class)
class MiRNAControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private MiRNAService miRNAService;

    @MockBean
    private PastSearchesService pastSearchesService;

    @Nested
    @DisplayName("GET /api/predictions")
    class GetPredictions {

        @Test
        @DisplayName("returns 200 OK with properly formatted JSON when all parameters are present")
        void testGetPredictions_Success() throws Exception {
            String[] mirnaArray = new String[]{"miR-1", "miR-2"};
            String[] toolsArray = new String[]{"ToolA", "ToolB"};
            String toolSelection = "UNION";
            String heuristic = "MAJORITY";

            Connection c1 = new Connection("ToolA", "0.95", "miR-1");
            Connection c2 = new Connection("ToolB", "0.80", "miR-2");

            Prediction.PredictionValues pv1 = new Prediction.PredictionValues(
                    "GeneX",
                    new String[]{"ToolA", "ToolB"},
                    new String[]{"Pathway1", "Pathway2"},
                    new Connection[]{c1, c2}
            );
            Prediction fakePrediction = new Prediction(
                    mirnaArray,
                    new Prediction.PredictionValues[]{pv1},
                    "1 s",
                    1,
                    2
            );

            when(miRNAService.getPredictions(
                    eq(mirnaArray), eq(toolsArray), eq(toolSelection), eq(heuristic)))
                    .thenReturn(fakePrediction);

            mockMvc.perform(get("/api/predictions")
                            .param("mirnaNames", mirnaArray)
                            .param("tools", toolsArray)
                            .param("toolSelection", toolSelection)
                            .param("heuristic", heuristic)
                            .accept(MediaType.APPLICATION_JSON))
                    .andExpect(status().isOk())
                    .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                    .andExpect(jsonPath("$.mirna[0]").value("miR-1"))
                    .andExpect(jsonPath("$.mirna[1]").value("miR-2"))
                    .andExpect(jsonPath("$.predictions").isArray())
                    .andExpect(jsonPath("$.predictions.length()").value(1))
                    .andExpect(jsonPath("$.predictions[0].gene").value("GeneX"))
                    .andExpect(jsonPath("$.predictions[0].tools[0]").value("ToolA"))
                    .andExpect(jsonPath("$.predictions[0].tools[1]").value("ToolB"))
                    .andExpect(jsonPath("$.predictions[0].pathways[0]").value("Pathway1"))
                    .andExpect(jsonPath("$.predictions[0].pathways[1]").value("Pathway2"))
                    .andExpect(jsonPath("$.predictions[0].connections[0].tool").value("ToolA"))
                    .andExpect(jsonPath("$.predictions[0].connections[0].quality").value("0.95"))
                    .andExpect(jsonPath("$.predictions[0].connections[0].mirna").value("miR-1"))
                    .andExpect(jsonPath("$.predictions[0].connections[1].tool").value("ToolB"))
                    .andExpect(jsonPath("$.predictions[0].connections[1].quality").value("0.80"))
                    .andExpect(jsonPath("$.predictions[0].connections[1].mirna").value("miR-2"))
                    .andExpect(jsonPath("$.searchTime").value("1 s"))
                    .andExpect(jsonPath("$.geneCount").value(1))
                    .andExpect(jsonPath("$.pathwayCount").value(2));

            ArgumentCaptor<Search> searchCaptor = ArgumentCaptor.forClass(Search.class);
            verify(pastSearchesService, times(1)).saveSearchAsync(searchCaptor.capture());

            Search capturedSearch = searchCaptor.getValue();
            assertThat(capturedSearch.getMirnaNames()).containsExactly("miR-1", "miR-2");
            assertThat(capturedSearch.getTools()).containsExactly("ToolA", "ToolB");
            assertThat(capturedSearch.getToolSelection()).isEqualTo("UNION");
            assertThat(capturedSearch.getHeuristic()).isEqualTo("MAJORITY");

            verify(miRNAService, times(1))
                    .getPredictions(eq(mirnaArray), eq(toolsArray), eq(toolSelection), eq(heuristic));
        }

        @Test
        @DisplayName("returns 400 Bad Request when a required parameter is missing")
        void testGetPredictions_MissingParameters() throws Exception {
            mockMvc.perform(get("/api/predictions")
                            .param("mirnaNames", "miR-1")
                            .accept(MediaType.APPLICATION_JSON))
                    .andExpect(status().isBadRequest());

            verifyNoInteractions(miRNAService);
            verifyNoInteractions(pastSearchesService);
        }
    }
}