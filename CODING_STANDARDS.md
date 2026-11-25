# Coding standards

The rules every change follows, checked in review.

## Layers

All code sits under `com.harvester.socialmediaharvester`, packaged by layer. Every new file, package or folder follows this layout; a class's suffix or annotation decides its package:

- `config`: wiring only. `*Config`, `*Properties` and `@Configuration` classes live here. `*Config` classes (`@Configuration(proxyBeanMethods = false)`) build beans and take other beans as `@Bean` method arguments. `*Properties` records are `@Validated` and registered with `@EnableConfigurationProperties` on a config class. A setting needed only in some situations (the first-Admin settings, needed only on an empty database) carries no constraint; the service that needs it checks it and fails with a message naming the environment variables. Startup triggers (an `ApplicationRunner` bean) live here and call a service for the work. Startup guards (`EnvironmentPostProcessor`, Flyway customizers) live here too.
- `controller`: HTTP only; `*Controller`, `@RestController` and `@Controller` classes, which reach data through services and depend on no repository. Read the request, call a service, map the result to a `model/dto` record. Return DTOs, never entities. The one exception is a static server-rendered page such as the sign-in form, which `SignInController` returns as HTML with no service call.
- `service`: the behaviour. Concrete `*Service` and `@Service` classes; they own repository calls and business rules.
- `model`: `@Table` entities and enums. `model/dto`: API records.
- `repository`: Spring Data R2DBC interfaces; every Spring Data repository and `*Repository` type.
- Add `mapper` or `exception` only when a feature needs one; leave no empty packages.

Constructor injection with final fields everywhere.

## Interfaces

Write a concrete class. Add an interface only when there are several real implementations (a per-Platform `Harvester`), when a framework needs one (Spring Data repositories), or for a contract between modules. Names carry no `I` prefix and no `Impl` suffix.

## Reactive code

ADR 0010 ([docs/adr/0010-reactive-stack-end-to-end.md](docs/adr/0010-reactive-stack-end-to-end.md)) is the rulebook. In review, look for:

- Blocking work (password hashing, file IO, a blocking library) wrapped in `Mono.fromCallable(...).subscribeOn(Schedulers.boundedElastic())`.
- Methods returning `Mono`/`Flux` and composing them; a `subscribe()` inside application code drops errors and is a bug.
- Never block on a reactive thread (event loop or `parallel` scheduler). `.block()` is allowed only on a thread you control (startup, tests, a dedicated job), with a comment saying why the code can't stay reactive. Inside request handling, compose with `flatMap`/`zip` instead. Blocking libraries run on `Schedulers.boundedElastic()`.
- JDBC (`java.sql`, `javax.sql`, Spring JDBC) in main code only in the `config.Flyway*` classes and `config.DatabaseCredentialsCheck`; Flyway migrations are the only JDBC use.
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
- BlockHound allow-list entries live in `support.BlockHoundAllowList`, and each one needs a comment saying why the call is safe.
- Tests touch only `harvester_test`. Assertions on credentials compare booleans so a failure never prints a value.
