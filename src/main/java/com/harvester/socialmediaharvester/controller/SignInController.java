package com.harvester.socialmediaharvester.controller;

import org.springframework.http.MediaType;
import org.springframework.security.web.server.csrf.CsrfToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.util.HtmlUtils;

import reactor.core.publisher.Mono;

/** The email and password form posted to {@code /login}. */
@RestController
public class SignInController {

	@GetMapping(path = "/login", produces = MediaType.TEXT_HTML_VALUE)
	Mono<String> signInPage(ServerWebExchange exchange) {
		Mono<CsrfToken> token = exchange.getAttributeOrDefault(CsrfToken.class.getName(), Mono.empty());
		boolean failed = exchange.getRequest().getQueryParams().containsKey("error");
		boolean signedOut = exchange.getRequest().getQueryParams().containsKey("logout");
		return token.map(csrf -> html(csrf, failed, signedOut))
				.defaultIfEmpty(html(null, failed, signedOut));
	}

	private static String html(CsrfToken csrf, boolean failed, boolean signedOut) {
		String csrfField = csrf == null ? ""
				: "<input type=\"hidden\" name=\"%s\" value=\"%s\">".formatted(
						HtmlUtils.htmlEscape(csrf.getParameterName()), HtmlUtils.htmlEscape(csrf.getToken()));
		String message = failed ? "<p role=\"alert\">Wrong email or password.</p>"
				: signedOut ? "<p role=\"status\">You have been logged out.</p>" : "";
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
