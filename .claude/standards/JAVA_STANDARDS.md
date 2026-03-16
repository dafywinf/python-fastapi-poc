# Java Engineering Standards (Google Style)

## 1. Code Style & Formatting

- **Guide:** Follow the [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html).
- **Indentation:** Use **2 spaces** per indent level (never tabs).
- **Column Limit:** 100 characters.
- **Braces:** Use "Egyptian brackets" (no line break before the opening brace). Always use braces for `if`, `else`, `for`, `do`, and `while` statements, even if empty.
- **Imports:** No wildcard imports. Group imports in this order: static imports, non-static imports.

## 2. Language Features

- **Version:** Assume **Java 21 LTS** features (Records, Sealed Classes, Pattern Matching for switch).
- **Optional:** Use `Optional` only for return types; never for fields or method parameters.
- **Variables:** Use `var` for local variables where the type is obvious.

## 3. Tooling & Testing

- **Build System:** Use **Maven**.
- **Testing:** Use **JUnit 5** and **AssertJ** for fluent assertions.
- **Mocking:** Use **Mockito** with constructor injection (avoid `@InjectMocks` where possible).
- **Documentation:** Follow standard Javadoc formatting for all public APIs.

## 4. Test Reporting (Allure)

- Annotate test classes with `@Feature` and test methods with `@Story` and `@Description`.
- Use `@Nested` inner classes to group: `TestCalculationLogic`, `TestEdgeCases`, `TestValidation`.
- Run with: `mvn test` (Allure results written to `target/allure-results/`).
- Generate report: `mvn allure:report` → opens at `target/site/allure-maven-plugin/index.html`.
