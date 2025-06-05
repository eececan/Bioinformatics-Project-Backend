package com.bioinformatics.bioinformatics;

import com.bioinformatics.bioinformatics.model.Connection;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.repository.MiRNARepository;
import com.bioinformatics.bioinformatics.model.Prediction.PredictionValues;
import com.bioinformatics.bioinformatics.model.GenePredictionDTO;
import com.bioinformatics.bioinformatics.service.MiRNAService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentMatchers;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.*;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

/**
 * Test suite for MiRNAService.getPredictions(...)
 */
@ExtendWith(MockitoExtension.class)
class MiRNAServiceTest {

    @Mock
    private MiRNARepository miRNARepository;

    @InjectMocks
    private MiRNAService miRNAService;

    // Common input parameters
    private String[] mirnaArray;
    private String[] toolsArray;
    private String toolSelection;
    private String heuristic;
    private List<String> mirnaList;
    private List<String> toolsList;

    @BeforeEach
    void setUp() {
        mirnaArray = new String[]{"miR-1", "miR-2"};
        toolsArray = new String[]{"ToolA", "ToolB"};
        toolSelection = "UNION";
        heuristic = "MAJORITY";

        // The service calls repository.getPredictions(List.of(mirnaNames), List.of(tools), …)
        mirnaList = List.of(mirnaArray);
        toolsList = List.of(toolsArray);
    }

    @Nested
    @DisplayName("When repository returns a non‐empty list of GenePredictionDTO")
    class NonEmptyRawPredictions {

        @Test
        @DisplayName("getPredictions(...) should map raw DTOs into a populated Prediction object")
        void testGetPredictions_WithResults() {
            Connection conn1 = new Connection("ToolA", "0.95", "miR-1");
            Connection conn2 = new Connection("ToolB", "0.80", "miR-2");

            GenePredictionDTO dto = new GenePredictionDTO(
                    "GeneX",
                    List.of("ToolA", "ToolB"),
                    List.of("Pathway1", "Pathway2"),
                    List.of(conn1, conn2)
            );

            when(miRNARepository.getPredictions(
                    eq(mirnaList),
                    eq(toolsList),
                    eq(toolSelection),
                    eq(heuristic)
            )).thenReturn(List.of(dto));

            Prediction result = miRNAService.getPredictions(
                    mirnaArray, toolsArray, toolSelection, heuristic
            );

            assertThat(result.getMirna()).containsExactly("miR-1", "miR-2");

            assertThat(result.getGeneCount()).isEqualTo(1);

            assertThat(result.getPathwayCount()).isEqualTo(2);

            String searchTime = result.getSearchTime();
            assertThat(searchTime).isNotNull()
                    .isNotEmpty()
                    .matches(".*\\s(ns|μs|ms|s|min\\s\\d+\\s?s)$");

            PredictionValues[] valuesArray = result.getPredictions();
            assertThat(valuesArray).hasSize(1);

            PredictionValues pv = valuesArray[0];
            assertThat(pv.getGene()).isEqualTo("GeneX");

            assertThat(pv.getTools()).containsExactly("ToolA", "ToolB");

            assertThat(pv.getPathways()).containsExactly("Pathway1", "Pathway2");

            Connection[] conns = pv.getConnections();
            assertThat(conns).hasSize(2);
            assertThat(conns[0].tool()).isEqualTo("ToolA");
            assertThat(conns[0].quality()).isEqualTo("0.95");
            assertThat(conns[0].mirna()).isEqualTo("miR-1");

            assertThat(conns[1].tool()).isEqualTo("ToolB");
            assertThat(conns[1].quality()).isEqualTo("0.80");
            assertThat(conns[1].mirna()).isEqualTo("miR-2");

            verify(miRNARepository, times(1)).getPredictions(
                    eq(mirnaList),
                    eq(toolsList),
                    eq(toolSelection),
                    eq(heuristic)
            );
        }
    }

    @Nested
    @DisplayName("When repository returns an empty list or null")
    class EmptyOrNullRawPredictions {

        @Test
        @DisplayName("getPredictions(...) with empty‐list rawPredictions yields zero geneCount and zero pathwayCount")
        void testGetPredictions_EmptyList() {
            when(miRNARepository.getPredictions(
                    eq(mirnaList),
                    eq(toolsList),
                    eq(toolSelection),
                    eq(heuristic)
            )).thenReturn(Collections.emptyList());

            Prediction result = miRNAService.getPredictions(
                    mirnaArray, toolsArray, toolSelection, heuristic
            );

            assertThat(result.getGeneCount()).isEqualTo(0);
            assertThat(result.getPathwayCount()).isEqualTo(0);
            assertThat(result.getPredictions()).isEmpty();

            assertThat(result.getMirna()).containsExactly("miR-1", "miR-2");

            String searchTime = result.getSearchTime();
            assertThat(searchTime).isNotNull()
                    .isNotEmpty()
                    .matches(".*\\s(ns|μs|ms|s|min\\s\\d+\\s?s)$");

            verify(miRNARepository, times(1)).getPredictions(
                    eq(mirnaList),
                    eq(toolsList),
                    eq(toolSelection),
                    eq(heuristic)
            );
        }

        @Test
        @DisplayName("getPredictions(...) with null rawPredictions yields zero geneCount and zero pathwayCount")
        void testGetPredictions_NullList() {
            when(miRNARepository.getPredictions(
                    eq(mirnaList),
                    eq(toolsList),
                    eq(toolSelection),
                    eq(heuristic)
            )).thenReturn(null);

            Prediction result = miRNAService.getPredictions(
                    mirnaArray, toolsArray, toolSelection, heuristic
            );

            assertThat(result.getGeneCount()).isEqualTo(0);
            assertThat(result.getPathwayCount()).isEqualTo(0);
            assertThat(result.getPredictions()).isEmpty();

            assertThat(result.getMirna()).containsExactly("miR-1", "miR-2");

            String searchTime = result.getSearchTime();
            assertThat(searchTime).isNotNull()
                    .isNotEmpty()
                    .matches(".*\\s(ns|μs|ms|s|min\\s\\d+\\s?s)$");

            verify(miRNARepository, times(1)).getPredictions(
                    eq(mirnaList),
                    eq(toolsList),
                    eq(toolSelection),
                    eq(heuristic)
            );
        }
    }
}