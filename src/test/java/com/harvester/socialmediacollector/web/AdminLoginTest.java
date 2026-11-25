package com.harvester.socialmediacollector.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.harvester.socialmediacollector.harness.HarvesterTest;
import com.harvester.socialmediacollector.harness.Login;

@HarvesterTest
class AdminLoginTest {

	// Seeded from application-test.properties on the freshly migrated harvester_test.
	static final String ADMIN_EMAIL = "first.admin@harvester.test";
	static final String ADMIN_PASSWORD = "first-admin-test-password";

	@Autowired
	WebTestClient client;

	@Test
	void firstAdminLogsInWithEmailAndPassword() {
		Login.as(client, ADMIN_EMAIL, ADMIN_PASSWORD)
				.get().uri("/api/me").exchange()
				.expectStatus().isOk()
				.expectBody()
				.jsonPath("$.email").isEqualTo(ADMIN_EMAIL)
				.jsonPath("$.role").isEqualTo("ADMIN");
	}

	@Test
	void emailIsMatchedIgnoringCase() {
		Login.as(client, ADMIN_EMAIL.toUpperCase(), ADMIN_PASSWORD)
				.get().uri("/api/me").exchange()
				.expectStatus().isOk()
				.expectBody().jsonPath("$.email").isEqualTo(ADMIN_EMAIL);
	}

	@Test
	void wrongPasswordIsRefused() {
		Login.submit(client, ADMIN_EMAIL, "not-the-password")
				.expectStatus().isFound()
				.expectHeader().location("/login?error");
	}

	@Test
	void unknownEmailIsRefused() {
		Login.submit(client, "nobody@harvester.test", ADMIN_PASSWORD)
				.expectStatus().isFound()
				.expectHeader().location("/login?error");
	}
}
