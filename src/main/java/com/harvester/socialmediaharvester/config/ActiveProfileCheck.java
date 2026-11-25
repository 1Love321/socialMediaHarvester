package com.harvester.socialmediaharvester.config;

import java.util.Arrays;

import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;

/**
 * Stops startup unless the active profiles choose a database. There is no
 * default profile: the profile picks the database, so it is always chosen from
 * outside with {@code SPRING_PROFILES_ACTIVE}. Runs after the config files are
 * loaded and before {@link DatabaseCredentialsCheck}.
 */
public class ActiveProfileCheck implements EnvironmentPostProcessor, Ordered {

	private static final String PROFILES = "local, dev or prod (tests use the test profile)";

	@Override
	public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
		String[] active = environment.getActiveProfiles();
		if (active.length == 0) {
			throw new IllegalStateException("No Spring profile is active. Set SPRING_PROFILES_ACTIVE to "
					+ PROFILES + " before starting the app.");
		}
		if (!environment.containsProperty("harvester.db.name")) {
			throw new IllegalStateException("The active profile " + Arrays.toString(active)
					+ " chooses no database. Set SPRING_PROFILES_ACTIVE to " + PROFILES + ".");
		}
	}

	@Override
	public int getOrder() {
		return Ordered.LOWEST_PRECEDENCE - 1;
	}
}
