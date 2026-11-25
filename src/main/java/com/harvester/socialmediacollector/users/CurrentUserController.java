package com.harvester.socialmediacollector.users;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import reactor.core.publisher.Mono;

/** Who is logged in, so the React app can shape itself to the role. */
@RestController
class CurrentUserController {

	private final UserAccountRepository accounts;

	CurrentUserController(UserAccountRepository accounts) {
		this.accounts = accounts;
	}

	record CurrentUser(String email, Role role) {
	}

	@GetMapping("/api/me")
	Mono<CurrentUser> currentUser(@AuthenticationPrincipal UserDetails principal) {
		return accounts.findByEmailIgnoringCase(principal.getUsername())
				.map(account -> new CurrentUser(account.email(), account.role()));
	}
}
