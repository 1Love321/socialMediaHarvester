package com.harvester.socialmediaharvester.config;

import java.util.Arrays;
import java.util.List;
import java.util.Set;

import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.core.Ordered;
import org.springframework.core.env.ConfigurableEnvironment;

/**
 * Stops startup unless exactly one environment profile is active and it chooses
 * a database. Spring's implicit {@code default} profile is never used: the profile
 * picks the database, so it is always chosen from outside with
 * {@code SPRING_PROFILES_ACTIVE}. Runs after the config files are
 * loaded and before {@link DatabaseCredentialsCheck}.
 */
public class ActiveProfileCheck implements EnvironmentPostProcessor, Ordered {

	private static final String PROFILES = "local, dev or prod (tests use the test profile)";

	private static final Set<String> ENVIRONMENT_PROFILES = Set.of("local", "dev", "prod", "test");

	@Override
	public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
		String[] active = environment.getActiveProfiles();
		if (active.length == 0) {
			throw new IllegalStateException("No Spring profile is active. Set SPRING_PROFILES_ACTIVE to "
					+ PROFILES + " before starting the app.");
		}
		List<String> environments = Arrays.stream(active).filter(ENVIRONMENT_PROFILES::contains).toList();
		if (environments.size() > 1) {
			throw new IllegalStateException("Only one environment profile may be active, but " + environments
					+ " are. Set SPRING_PROFILES_ACTIVE to one of " + PROFILES + ".");
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
