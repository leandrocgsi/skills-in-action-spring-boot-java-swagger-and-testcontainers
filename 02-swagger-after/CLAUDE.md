# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A REST API for people (CRUD with HATEOAS links) built on Spring Boot 4.1.1 and Java 25. It is the working project for a "skills in action" video series where Swagger/OpenAPI documentation and Testcontainers integration tests are added with Claude Code. The target state:

- springdoc OpenAPI + Swagger UI, with API metadata (title, version, description, license) in an `OpenApiConfig`
- `@Tag` on controllers, documented through `*ControllerDocs` interfaces carrying `@Operation`/`@ApiResponse`
- a Book resource alongside Person, also documented
- Testcontainers (MySQL) + REST Assured integration tests, a Swagger UI test, and an abstract base class that starts the container and injects the datasource

None of that exists yet: the code is Person-only, with no OpenAPI and no integration tests. All Maven commands run from this directory.

## Stack

Maven, MySQL, Flyway, Spring Data JPA, Spring HATEOAS, Dozer 7 for mapping. Boot 4 specifics: starters are `spring-boot-starter-webmvc`, `-flyway`, `-data-jpa-test`, and Jackson 3 (`tools.jackson.*` packages; XML/YAML via `tools.jackson.dataformat`). Check Boot 4 / Jackson 3 compatibility when adding libraries (e.g. springdoc version).

## Commands

```
mvn spring-boot:run                      # needs MySQL (below)
mvn test                                 # all tests
mvn test -Dtest=PersonServicesTest       # one class
mvn test -Dtest=PersonServicesTest#testName   # one method
mvn flyway:migrate                       # plugin is preconfigured against local MySQL
```

Runtime needs MySQL on `localhost:3306`, database `skills_in_action_claude_code_swagger_erudio` (create it manually), user `root` / password `admin123`. The DB name and credentials are duplicated in `src/main/resources/application.yml`, `src/test/resources/application.yml` and the `flyway-maven-plugin` config in `pom.xml`; change all three together. Flyway fails with a checksum mismatch if the database was migrated by a different version of `V1`, so use a fresh database rather than reusing an old one. Migrations in `src/main/resources/db/migration` create and seed the table on startup; `ddl-auto` is `none`.

`StartupTests` (context load) needs that MySQL reachable; `src/test/resources/application.yml` replaces (not merges with) the main one, so it repeats the datasource settings. The other tests are plain unit tests (Mockito).

The surefire `argLine` loads Mockito as a `-javaagent` via the `maven-dependency-plugin` `properties` goal (`${org.mockito:mockito-core:jar}`) plus `--enable-native-access=ALL-UNNAMED`. Keep both plugins in place or tests will warn/fail on newer JDKs.

## Architecture

Layered package `br.com.erudio`: `controllers` -> `services` -> `repository` (Spring Data JPA) -> `model` (entities). `data.dto` holds DTOs, `exception` holds custom exceptions plus `exception.hadler.CustomEntityResponseHandler` (note the `hadler` typo is the real package name) for centralized error responses.

Points that span multiple files:

- **DTO <-> entity mapping** goes through the static helper `mapper.ObjectMapper` (Dozer), via `parseObject` / `parseListObjects`. Services call it; don't hand-map in new code. It shadows Jackson's `ObjectMapper` name, so watch imports.
- **HATEOAS links are added in the service layer** (`PersonServices.addHateoasLinks`) using `linkTo(methodOn(PersonController.class)...)`, so services depend on controllers. `PersonDTO` extends HATEOAS `RepresentationModel<PersonDTO>`. New endpoints must be added to that link set to appear in responses.
- **Content negotiation** is JSON/XML/YAML. `config.WebConfig` selects by `Accept` header (default JSON), and every controller mapping lists all three media types in `produces`/`consumes`. New endpoints should do the same. `config.JacksonConfig` only customizes the YAML converter (NON_NULL inclusion) through `ServerHttpMessageConvertersCustomizer`.
- Jackson 3 split: annotations stay in `com.fasterxml.jackson.annotation`, while mappers/modules are `tools.jackson.*`. Don't import Jackson 2 `com.fasterxml.jackson.databind` classes.
- Base path is `/api/person/v1`; `TestLogController` (`/api/test/v1`) is a logging demo endpoint.
- Controllers return DTOs directly and throw custom exceptions; there is no `ResponseEntity` wrapping except `delete` (204).
- Controllers and services use field `@Autowired` injection.
