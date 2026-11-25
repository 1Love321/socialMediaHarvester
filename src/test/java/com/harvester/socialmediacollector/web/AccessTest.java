package com.harvester.socialmediacollector.web;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.MediaType;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.harvester.socialmediacollector.harness.AppTest;

@AppTest
class AccessTest {

	@Autowired
	WebTestClient client;

	@Test
	void healthIsReachableWithoutSigningIn() {
		client.get().uri("/actuator/health").exchange()
				.expectStatus().isOk()
				.expectBody().jsonPath("$.status").isEqualTo("UP");
	}

	@Test
	void anonymousHealthCheckStartsNoSession() {
		var response = client.get().uri("/actuator/health").exchange()
				.expectStatus().isOk()
				.returnResult(Void.class);

		assertThat(response.getResponseCookies()).doesNotContainKey("SESSION");
	}

	@Test
	void signInPageIsReachableWithoutSigningIn() {
		client.get().uri("/login").exchange()
				.expectStatus().isOk();
	}

	@ParameterizedTest
	@ValueSource(strings = { "/", "/index.html", "/actuator/info", "/anything" })
	void pagesRedirectToSignInWithoutSigningIn(String path) {
		client.get().uri(path).accept(MediaType.TEXT_HTML).exchange()
				.expectStatus().isFound()
				.expectHeader().location("/login");
	}

	@ParameterizedTest
	@ValueSource(strings = { "/api/me", "/api/anything" })
	void apiIsUnauthorizedWithoutSigningIn(String path) {
		client.get().uri(path).accept(MediaType.TEXT_HTML).exchange()
				.expectStatus().isUnauthorized();
	}
}
