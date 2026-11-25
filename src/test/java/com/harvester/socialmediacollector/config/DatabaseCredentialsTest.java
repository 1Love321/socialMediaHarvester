package com.harvester.socialmediacollector.config;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.SpringApplication;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;

import com.harvester.socialmediacollector.SocialmediacollectorApplication;

/** Startup refuses to go on without the database login from the environment. */
class DatabaseCredentialsTest {

	@ParameterizedTest
	@ValueSource(strings = { "DB_USER_HARVEST", "DB_PASSWORD_HARVEST" })
	void startupFailsClearlyWhenAVariableIsMissing(String missing) {
		assertThatThrownBy(() -> startWithEnvironmentWithout(missing, null))
				.hasStackTraceContaining("Environment variable " + missing + " is not set");
	}

	@ParameterizedTest
	@ValueSource(strings = { "DB_USER_HARVEST", "DB_PASSWORD_HARVEST" })
	void startupFailsClearlyWhenAVariableIsBlank(String blank) {
		assertThatThrownBy(() -> startWithEnvironmentWithout(blank, " "))
				.hasStackTraceContaining("Environment variable " + blank + " is not set");
	}

	private static void startWithEnvironmentWithout(String variable, String replacement) {
		Map<String, Object> variables = new HashMap<>(System.getenv());
		variables.remove(variable);
		if (replacement != null) {
			variables.put(variable, replacement);
		}
		StandardEnvironment environment = new StandardEnvironment();
		environment.getPropertySources().replace(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME,
				new MapPropertySource(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, variables));
		SpringApplication app = new SpringApplication(SocialmediacollectorApplication.class);
		app.setEnvironment(environment);
		app.setAdditionalProfiles("test");
		app.run().close();
	}
}
