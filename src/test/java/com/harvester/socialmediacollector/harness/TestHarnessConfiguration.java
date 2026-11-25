package com.harvester.socialmediacollector.harness;

import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

@TestConfiguration(proxyBeanMethods = false)
public class TestHarnessConfiguration {

	/** Wipes harvester_test and rebuilds it from the migrations whenever a test context starts. */
	@Bean
	FlywayMigrationStrategy cleanThenMigrate() {
		return flyway -> {
			flyway.clean();
			flyway.migrate();
		};
	}

	@Bean
	@Primary
	TestClock testClock() {
		return new TestClock();
	}

	@Bean(destroyMethod = "close")
	PlatformApiStub platformApiStub() {
		return new PlatformApiStub();
	}
}
