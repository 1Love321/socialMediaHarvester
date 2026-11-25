package com.harvester.socialmediaharvester.config;

import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;

/**
 * Stops startup when no profile is active. There is no default profile: the
 * profile picks the database, so it is always chosen from outside with
 * {@code SPRING_PROFILES_ACTIVE}. Runs after the config files are loaded and
 * before {@link DatabaseCredentialsCheck}.
 */
public class ActiveProfileCheck implements EnvironmentPostProcessor, Ordered {

	@Override
	public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
		if (environment.getActiveProfiles().length == 0) {
			throw new IllegalStateException("No Spring profile is active. Set SPRING_PROFILES_ACTIVE to "
					+ "local, dev or prod before starting the app (tests use the test profile).");
		}
	}

	@Override
	public int getOrder() {
		return Ordered.LOWEST_PRECEDENCE - 1;
	}
}
