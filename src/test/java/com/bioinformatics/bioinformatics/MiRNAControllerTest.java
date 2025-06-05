package bioinformatics;
import com.bioinformatics.bioinformatics.controller.MiRNAController;
import com.bioinformatics.bioinformatics.model.Prediction;
import com.bioinformatics.bioinformatics.model.Prediction.PredictionValues;
import com.bioinformatics.bioinformatics.model.Search;
import com.bioinformatics.bioinformatics.service.MiRNAService;
import com.bioinformatics.bioinformatics.service.PastSearchesService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.ResponseEntity;

import java.util.Arrays;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class MiRNAControllerTest {

    @Mock
    private MiRNAService miRNAService;

    @Mock
    private PastSearchesService pastSearchesService;

    @InjectMocks
    private MiRNAController miRNAController;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void testGetPredictions_NormalInput_ShouldReturnPredictionAndSaveSearch() {
        // Arrange
        String[] mirnaNames = {"miR-21", "miR-155"};
        String[] tools = {"ToolA", "ToolB"};
        String toolSelection = "UNION";
        String heuristic = "MAJORITY";

        // Create dummy PredictionValues
        PredictionValues pv1 = new PredictionValues("GeneX", new String[]{"ToolA"}, new String[]{"Pathway1", "Pathway2"});
        PredictionValues pv2 = new PredictionValues("GeneY", new String[]{"ToolB"}, new String[]{"Pathway3"});
        PredictionValues[] predictionValuesArray = new PredictionValues[]{pv1, pv2};

        // Create dummy Prediction
        Prediction dummyPrediction = new Prediction(mirnaNames, predictionValuesArray, "2025-06-05T12:00:00Z", 2, 3);

        when(miRNAService.getPredictions(mirnaNames, tools, toolSelection, heuristic)).thenReturn(dummyPrediction);

        // Act
        ResponseEntity<Prediction> response = miRNAController.getPredictions(mirnaNames, tools, toolSelection, heuristic);

        // Assert: Response status and body
        assertNotNull(response, "Response should not be null");
        assertEquals(200, response.getStatusCodeValue(), "Status code should be 200 OK");
        Prediction result = response.getBody();
        assertNotNull(result, "Response body should not be null");
        assertArrayEquals(mirnaNames, result.getMirna(), "miRNA arrays should match");
        assertEquals(2, result.getGeneCount(), "Gene count should be 2");
        assertEquals(3, result.getPathwayCount(), "Pathway count should be 3");
        assertEquals(2, result.getPredictions().length, "There should be 2 prediction entries");

        // Assert: pastSearchesService.saveSearchAsync was called with correct Search object
        ArgumentCaptor<Search> searchCaptor = ArgumentCaptor.forClass(Search.class);
        verify(pastSearchesService, times(1)).saveSearchAsync(searchCaptor.capture());
        Search capturedSearch = searchCaptor.getValue();
        // Verify the Search object's fields
        List<String> expectedMirnas = Arrays.asList(mirnaNames);
        List<String> expectedTools = Arrays.asList(tools);
        assertEquals(new java.util.HashSet<>(expectedMirnas), new java.util.HashSet<>(capturedSearch.getmirnaNames()), "miRNA names in Search should match");
        assertEquals(new java.util.HashSet<>(expectedTools), new java.util.HashSet<>(capturedSearch.getTools()), "Tools in Search should match");
        assertEquals(toolSelection, capturedSearch.getToolSelection(), "Tool selection should match");
        assertEquals(heuristic, capturedSearch.getHeuristic(), "Heuristic should match");
    }

    @Test
    void testGetPredictions_EmptyInput_ShouldReturnEmptyPredictionAndSaveSearch() {
        // Arrange with empty arrays
        String[] mirnaNames = {};
        String[] tools = {};
        String toolSelection = "INTERSECTION";
        String heuristic = "INTERSECTION";

        // Create dummy Prediction for empty input
        PredictionValues[] predictionValuesArray = new PredictionValues[0];
        Prediction dummyPrediction = new Prediction(mirnaNames, predictionValuesArray, "2025-06-05T12:00:00Z", 0, 0);

        when(miRNAService.getPredictions(mirnaNames, tools, toolSelection, heuristic)).thenReturn(dummyPrediction);

        // Act
        ResponseEntity<Prediction> response = miRNAController.getPredictions(mirnaNames, tools, toolSelection, heuristic);

        // Assert: Response and body
        assertNotNull(response, "Response should not be null");
        assertEquals(200, response.getStatusCodeValue(), "Status code should be 200 OK");
        Prediction result = response.getBody();
        assertNotNull(result, "Response body should not be null");
        assertEquals(0, result.getGeneCount(), "Gene count should be 0 for empty input");
        assertEquals(0, result.getPathwayCount(), "Pathway count should be 0 for empty input");
        assertEquals(0, result.getPredictions().length, "Prediction array should be empty");

        // Assert: pastSearchesService.saveSearchAsync was called
        ArgumentCaptor<Search> searchCaptor = ArgumentCaptor.forClass(Search.class);
        verify(pastSearchesService, times(1)).saveSearchAsync(searchCaptor.capture());
        Search capturedSearch = searchCaptor.getValue();
        assertTrue(capturedSearch.getmirnaNames().isEmpty(), "miRNA names in Search should be empty");
        assertTrue(capturedSearch.getTools().isEmpty(), "Tools in Search should be empty");
        assertEquals(toolSelection, capturedSearch.getToolSelection(), "Tool selection should match");
        assertEquals(heuristic, capturedSearch.getHeuristic(), "Heuristic should match");
    }
}
