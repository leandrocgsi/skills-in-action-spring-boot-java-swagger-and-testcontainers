package br.com.erudio.integrationtests.controllers.withjson;

import br.com.erudio.config.TestConfigs;
import br.com.erudio.integrationtests.dto.PersonDTO;
import br.com.erudio.integrationtests.testcontainers.AbstractIntegrationTest;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import tools.jackson.databind.DeserializationFeature;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.json.JsonMapper;

import static io.restassured.RestAssured.given;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.DEFINED_PORT)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class PersonControllerJsonTest extends AbstractIntegrationTest {

    private static ObjectMapper objectMapper;

    private static PersonDTO person;

    @BeforeAll
    static void setUp() {
        objectMapper = JsonMapper.builder()
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .build();
        person = new PersonDTO();
    }

    @Test
    @Order(1)
    void createTest() {
        person.setFirstName("Linus");
        person.setLastName("Torvalds");
        person.setAddress("Helsinki - Finland");
        person.setGender("Male");

        var content = given()
            .port(TestConfigs.SERVER_PORT)
            .basePath("/api/person/v1")
            .contentType(MediaType.APPLICATION_JSON_VALUE)
            .accept(MediaType.APPLICATION_JSON_VALUE)
            .body(person)
        .when()
            .post()
        .then()
            .statusCode(200)
        .extract()
            .body()
            .asString();

        PersonDTO created = objectMapper.readValue(content, PersonDTO.class);
        person = created;

        assertNotNull(created.getId());
        assertTrue(created.getId() > 0);
        assertEquals("Linus", created.getFirstName());
        assertEquals("Torvalds", created.getLastName());
        assertEquals("Helsinki - Finland", created.getAddress());
        assertEquals("Male", created.getGender());
    }

    @Test
    @Order(2)
    void findByIdTest() {
        var content = given()
            .port(TestConfigs.SERVER_PORT)
            .basePath("/api/person/v1")
            .accept(MediaType.APPLICATION_JSON_VALUE)
            .pathParam("id", person.getId())
        .when()
            .get("{id}")
        .then()
            .statusCode(200)
        .extract()
            .body()
            .asString();

        PersonDTO found = objectMapper.readValue(content, PersonDTO.class);

        assertEquals(person, found);
    }

    @Test
    @Order(3)
    void updateTest() {
        person.setLastName("Torvalds - Updated");

        var content = given()
            .port(TestConfigs.SERVER_PORT)
            .basePath("/api/person/v1")
            .contentType(MediaType.APPLICATION_JSON_VALUE)
            .accept(MediaType.APPLICATION_JSON_VALUE)
            .body(person)
        .when()
            .put()
        .then()
            .statusCode(200)
        .extract()
            .body()
            .asString();

        PersonDTO updated = objectMapper.readValue(content, PersonDTO.class);
        person = updated;

        assertEquals("Torvalds - Updated", updated.getLastName());
    }

    @Test
    @Order(4)
    void deleteTest() {
        given()
            .port(TestConfigs.SERVER_PORT)
            .basePath("/api/person/v1")
            .pathParam("id", person.getId())
        .when()
            .delete("{id}")
        .then()
            .statusCode(204);
    }

    @Test
    @Order(5)
    void findByIdAfterDeleteReturnsNotFoundTest() {
        given()
            .port(TestConfigs.SERVER_PORT)
            .basePath("/api/person/v1")
            .accept(MediaType.APPLICATION_JSON_VALUE)
            .pathParam("id", person.getId())
        .when()
            .get("{id}")
        .then()
            .statusCode(404);
    }

    @Test
    @Order(6)
    void findAllTest() {
        var content = given()
            .port(TestConfigs.SERVER_PORT)
            .basePath("/api/person/v1")
            .accept(MediaType.APPLICATION_JSON_VALUE)
        .when()
            .get()
        .then()
            .statusCode(200)
        .extract()
            .body()
            .asString();

        var people = objectMapper.readValue(content, PersonDTO[].class);

        assertFalse(people.length == 0);
        assertNotNull(people[0].getId());
        assertEquals("Ayrton", people[0].getFirstName());
    }
}
