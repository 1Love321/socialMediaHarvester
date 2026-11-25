package com.harvester.socialmediaharvester.config;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.boot.SpringApplication;
import org.springframework.core.env.MapPropertySource;
import org.springframework.core.env.StandardEnvironment;

import com.harvester.socialmediaharvester.SocialMediaHarvesterApplication;

/** There is no default profile: starting without one stops before any connection is attempted. */
class ActiveProfileCheckTest {

	@Test
	void startupWithoutAProfileFailsClearly() {
		Map<String, Object> variables = new HashMap<>(System.getenv());
		variables.remove("SPRING_PROFILES_ACTIVE");
		StandardEnvironment environment = new StandardEnvironment();
		environment.getPropertySources().replace(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME,
				new MapPropertySource(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME, variables));
		environment.getPropertySources().replace(StandardEnvironment.SYSTEM_PROPERTIES_PROPERTY_SOURCE_NAME,
				new MapPropertySource(StandardEnvironment.SYSTEM_PROPERTIES_PROPERTY_SOURCE_NAME, new HashMap<>()));
		SpringApplication app = new SpringApplication(SocialMediaHarvesterApplication.class);
		app.setEnvironment(environment);

		assertThatThrownBy(() -> app.run().close())
				.hasStackTraceContaining("No Spring profile is active. Set SPRING_PROFILES_ACTIVE");
	}
}
