# Coding standards

Judgement calls for review. Mechanical rules are ArchUnit tests (listed at the end); `mvn test` fails when one breaks, so they are not repeated here.

## Layers

All code sits under `com.harvester.socialmediaharvester`, packaged by layer:

- `config`: wiring only. `*Config` classes (`@Configuration(proxyBeanMethods = false)`) build beans and take other beans as `@Bean` method arguments. `*Properties` records are `@Validated` and registered with `@EnableConfigurationProperties` on a config class. A setting needed only in some situations (the first-Admin settings, needed only on an empty database) carries no constraint; the service that needs it checks it and fails with a message naming the environment variables. Startup triggers (an `ApplicationRunner` bean) live here and call a service for the work. Startup guards (`EnvironmentPostProcessor`, Flyway customizers) live here too.
- `controller`: HTTP only. Read the request, call a service, map the result to a `model/dto` record. Return DTOs, never entities. The one exception is a static server-rendered page such as the sign-in form, which `SignInController` returns as HTML with no service call.
- `service`: the behaviour. Concrete `*Service` classes; they own repository calls and business rules.
- `model`: entities and enums. `model/dto`: API records.
- `repository`: Spring Data R2DBC interfaces.
- Add `mapper` or `exception` only when a feature needs one; leave no empty packages.

Constructor injection with final fields everywhere.

## Interfaces

Write a concrete class. Add an interface only when there are several real implementations (a per-Platform `Harvester`), when a framework needs one (Spring Data repositories), or for a contract between modules. Names carry no `I` prefix and no `Impl` suffix.

## Reactive code

ADR 0010 ([docs/adr/0010-reactive-stack-end-to-end.md](docs/adr/0010-reactive-stack-end-to-end.md)) is the rulebook. In review, look for:

- Blocking work (password hashing, file IO, a blocking library) wrapped in `Mono.fromCallable(...).subscribeOn(Schedulers.boundedElastic())`.
- Methods returning `Mono`/`Flux` and composing them; a `subscribe()` inside application code drops errors and is a bug.
- Time read from the injected `Clock`, never `Instant.now()`.

## Naming

Use the terms in [GLOSSARY.md](GLOSSARY.md) and none of their _Avoid_ words. A class named `Harvester*` is a per-Platform Harvester and nothing else. Say "sign in" in code and UI text; "Login" appears only as part of **Platform Login** and in the `/login` URL.

## Configuration

- YAML only. Shared settings in `application.yml`; `application-local.yml`, `application-dev.yml`, `application-prod.yml` in `src/main/resources`; `application-test.yml` in `src/test/resources`.
- Profiles are chosen from outside with `SPRING_PROFILES_ACTIVE`; no file activates a profile and there is no default profile.
- Each profile file names its own database host, port and name (issue #28).
- Secrets and deployment values come from environment variables. Database credentials come only from `DB_USER_HARVEST` / `DB_PASSWORD_HARVEST`, with no default. A required setting has no default, so a missing value fails startup with a message naming the variable.
- Logging: root `INFO`, application `${APP_LOG_LEVEL:INFO}`, `DEBUG` in `local`. Log messages never contain credentials or passwords; records holding them override `toString()`.

## Tests

- Test packages mirror main packages. The shared harness lives in the test-only `support` package: `@AppTest` boots the app against `harvester_test` with a `TestClock` and a `PlatformApiStub`.
- HTTP behaviour through `WebTestClient`, signing in with `support.SignIn`.
- Reactive results through `StepVerifier`. `.block()` is acceptable in test setup and teardown only.
- BlockHound runs in every test; a `BlockingOperationError` is a real bug in main code, not a test to silence.
- Tests touch only `harvester_test`. Assertions on credentials compare booleans so a failure never prints a value.

## Enforced by ArchUnit

`src/test/java/com/harvester/socialmediaharvester/architecture/ArchitectureTest.java`:

- Classes live in their layer: `*Config`, `*Properties` and `@Configuration` in `config`; `@RestController`/`@Controller` and `*Controller` in `controller`; `@Service` and `*Service` in `service`; `@Table` entities in `model`; Spring Data repositories and `*Repository` in `repository`.
- Controllers do not depend on repositories.
- No interface is named `I[A-Z]*`.
- No `Mono.block*` / `Flux.block*` in main code, except `service.FirstAdminService` (ADR 0010).
- No JDBC (`java.sql`, `javax.sql`, Spring JDBC) in main code, except `config.Flyway*` classes and `config.DatabaseCredentialsCheck`.
