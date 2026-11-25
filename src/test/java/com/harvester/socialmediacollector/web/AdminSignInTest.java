package com.harvester.socialmediacollector.web;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.harvester.socialmediacollector.harness.AppTest;
import com.harvester.socialmediacollector.harness.FirstAdmin;
import com.harvester.socialmediacollector.harness.SignIn;

@AppTest
class AdminSignInTest {

	@Autowired
	WebTestClient client;

	@Test
	void firstAdminSignsInWithEmailAndPassword() {
		SignIn.as(client, FirstAdmin.EMAIL, FirstAdmin.PASSWORD)
				.get().uri("/api/me").exchange()
				.expectStatus().isOk()
				.expectBody()
				.jsonPath("$.email").isEqualTo(FirstAdmin.EMAIL)
				.jsonPath("$.role").isEqualTo("ADMIN");
	}

	@Test
	void emailIsMatchedIgnoringCase() {
		SignIn.as(client, FirstAdmin.EMAIL.toUpperCase(), FirstAdmin.PASSWORD)
				.get().uri("/api/me").exchange()
				.expectStatus().isOk()
				.expectBody().jsonPath("$.email").isEqualTo(FirstAdmin.EMAIL);
	}

	@Test
	void wrongPasswordIsRefused() {
		SignIn.submit(client, FirstAdmin.EMAIL, "not-the-password")
				.expectStatus().isFound()
				.expectHeader().location("/login?error");
	}

	@Test
	void unknownEmailIsRefused() {
		SignIn.submit(client, "nobody@harvester.test", FirstAdmin.PASSWORD)
				.expectStatus().isFound()
				.expectHeader().location("/login?error");
	}
}
