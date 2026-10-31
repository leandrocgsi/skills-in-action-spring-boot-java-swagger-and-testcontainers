package br.com.erudio.controllers.docs;

import br.com.erudio.data.dto.PersonDTO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.List;

public interface PersonControllerDocs {

    @Operation(summary = "Find All People",
        description = "Finds All People",
        tags = {"Person"},
        responses = {
            @ApiResponse(description = "Success", responseCode = "200",
                content = @Content(
                    mediaType = MediaType.APPLICATION_JSON_VALUE,
                    array = @ArraySchema(schema = @Schema(implementation = PersonDTO.class)))),
            @ApiResponse(description = "Internal Server Error", responseCode = "500", content = @Content)
        })
    List<PersonDTO> findAll();

    @Operation(summary = "Finds a Person",
        description = "Find a specific Person by its ID",
        tags = {"Person"},
        responses = {
            @ApiResponse(description = "Success", responseCode = "200",
                content = @Content(schema = @Schema(implementation = PersonDTO.class))),
            @ApiResponse(description = "Not Found", responseCode = "404", content = @Content),
            @ApiResponse(description = "Internal Server Error", responseCode = "500", content = @Content)
        })
    PersonDTO findById(@PathVariable("id") Long id);

    @Operation(summary = "Create a Person",
        description = "Creates a new Person by passing in a JSON, XML or YAML representation",
        tags = {"Person"},
        responses = {
            @ApiResponse(description = "Success", responseCode = "200",
                content = @Content(schema = @Schema(implementation = PersonDTO.class))),
            @ApiResponse(description = "Bad Request", responseCode = "400", content = @Content),
            @ApiResponse(description = "Internal Server Error", responseCode = "500", content = @Content)
        })
    PersonDTO create(@RequestBody PersonDTO person);

    @Operation(summary = "Update a Person",
        description = "Updates a Person by passing in a JSON, XML or YAML representation",
        tags = {"Person"},
        responses = {
            @ApiResponse(description = "Success", responseCode = "200",
                content = @Content(schema = @Schema(implementation = PersonDTO.class))),
            @ApiResponse(description = "Bad Request", responseCode = "400", content = @Content),
            @ApiResponse(description = "Not Found", responseCode = "404", content = @Content),
            @ApiResponse(description = "Internal Server Error", responseCode = "500", content = @Content)
        })
    PersonDTO update(@RequestBody PersonDTO person);

    @Operation(summary = "Delete a Person",
        description = "Deletes a Person by its ID",
        tags = {"Person"},
        responses = {
            @ApiResponse(description = "No Content", responseCode = "204", content = @Content),
            @ApiResponse(description = "Not Found", responseCode = "404", content = @Content),
            @ApiResponse(description = "Internal Server Error", responseCode = "500", content = @Content)
        })
    ResponseEntity<?> delete(@PathVariable("id") Long id);
}
