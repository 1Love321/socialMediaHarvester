package com.harvester.socialmediacollector.config;

import java.util.List;

import org.springframework.boot.EnvironmentPostProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.util.StringUtils;

/**
 * Stops startup before any connection is attempted when the database login is
 * missing. It only ever names the variables, never their values.
 */
public class DatabaseCredentialsCheck implements EnvironmentPostProcessor {

	static final List<String> VARIABLES = List.of("DB_USER_HARVEST", "DB_PASSWORD_HARVEST");

	@Override
	public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
		for (String variable : VARIABLES) {
			if (!StringUtils.hasText(environment.getProperty(variable))) {
				throw new IllegalStateException("Environment variable " + variable + " is not set. The harvester "
						+ "reads its database login only from DB_USER_HARVEST and DB_PASSWORD_HARVEST; "
						+ "set both before starting it.");
			}
		}
	}
}
