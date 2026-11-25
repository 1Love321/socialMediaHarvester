package com.harvester.socialmediacollector.web;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.MediaType;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.harvester.socialmediacollector.harness.HarvesterTest;

@HarvesterTest
class AccessTest {

	@Autowired
	WebTestClient client;

	@Test
	void healthIsReachableWithoutLogin() {
		// Reachability only: whether the shared PostgreSQL server answers in time is not this test's concern.
		client.get().uri("/actuator/health").exchange()
				.expectStatus().value(status -> assertThat(status).isIn(200, 503))
				.expectBody().jsonPath("$.status").isNotEmpty();
	}

	@Test
	void loginPageIsReachableWithoutLogin() {
		client.get().uri("/login").exchange()
				.expectStatus().isOk();
	}

	@ParameterizedTest
	@ValueSource(strings = { "/", "/index.html", "/actuator/info", "/anything" })
	void pagesRedirectToLoginWithoutLogin(String path) {
		client.get().uri(path).accept(MediaType.TEXT_HTML).exchange()
				.expectStatus().isFound()
				.expectHeader().location("/login");
	}

	@ParameterizedTest
	@ValueSource(strings = { "/api/me", "/api/anything" })
	void apiIsUnauthorizedWithoutLogin(String path) {
		client.get().uri(path).accept(MediaType.TEXT_HTML).exchange()
				.expectStatus().isUnauthorized();
	}
}
