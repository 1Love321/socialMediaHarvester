package com.harvester.socialmediacollector.web;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.test.web.reactive.server.WebTestClient;

import com.harvester.socialmediacollector.harness.HarvesterTest;
import com.harvester.socialmediacollector.harness.Login;

/** The Maven build bundles the React app and Spring Boot serves it after login. */
@HarvesterTest
class ReactAppTest {

	@Autowired
	WebTestClient client;

	@Test
	void loggedInUserGetsTheReactAppWithItsAssetsReachable() {
		String page = Login.as(client, AdminLoginTest.ADMIN_EMAIL, AdminLoginTest.ADMIN_PASSWORD)
				.get().uri("/").accept(MediaType.TEXT_HTML).exchange()
				.expectStatus().isOk()
				.expectBody(String.class).returnResult().getResponseBody();

		assertThat(page).contains("<div id=\"root\"></div>");
		Matcher script = Pattern.compile("src=\"(/assets/[^\"]+\\.js)\"").matcher(page);
		assertThat(script.find()).as("index.html references a bundled script").isTrue();

		client.get().uri(script.group(1)).exchange()
				.expectStatus().isOk();
	}
}
