package com.harvester.socialmediacollector.security;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.web.server.csrf.CsrfToken;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.RouterFunctions;
import org.springframework.web.reactive.function.server.ServerRequest;
import org.springframework.web.reactive.function.server.ServerResponse;
import org.springframework.web.util.HtmlUtils;

import reactor.core.publisher.Mono;

/** The email and password form posted to {@code /login}. */
@Configuration(proxyBeanMethods = false)
public class LoginPage {

	@Bean
	RouterFunction<ServerResponse> loginPageRoute() {
		return RouterFunctions.route().GET("/login", LoginPage::render).build();
	}

	private static Mono<ServerResponse> render(ServerRequest request) {
		Mono<CsrfToken> token = request.exchange().getAttributeOrDefault(CsrfToken.class.getName(), Mono.empty());
		boolean failed = request.queryParam("error").isPresent();
		boolean loggedOut = request.queryParam("logout").isPresent();
		return token.map(csrf -> html(csrf, failed, loggedOut))
				.defaultIfEmpty(html(null, failed, loggedOut))
				.flatMap(body -> ServerResponse.ok().contentType(MediaType.TEXT_HTML).bodyValue(body));
	}

	private static String html(CsrfToken csrf, boolean failed, boolean loggedOut) {
		String csrfField = csrf == null ? ""
				: "<input type=\"hidden\" name=\"%s\" value=\"%s\">".formatted(
						HtmlUtils.htmlEscape(csrf.getParameterName()), HtmlUtils.htmlEscape(csrf.getToken()));
		String message = failed ? "<p role=\"alert\">Wrong email or password.</p>"
				: loggedOut ? "<p role=\"status\">You have been logged out.</p>" : "";
		return """
				<!doctype html>
				<html lang="en">
				<head><meta charset="utf-8"><title>Sign in - Social Media Harvester</title></head>
				<body>
				<main>
				<h1>Sign in</h1>
				%s
				<form method="post" action="/login">
				<label>Email <input type="email" name="username" autocomplete="username" required autofocus></label>
				<label>Password <input type="password" name="password" autocomplete="current-password" required></label>
				%s
				<button type="submit">Sign in</button>
				</form>
				</main>
				</body>
				</html>
				""".formatted(message, csrfField);
	}
}
