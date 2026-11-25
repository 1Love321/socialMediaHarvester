package com.harvester.socialmediacollector.users;

import org.springframework.security.core.userdetails.ReactiveUserDetailsService;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Service;

import reactor.core.publisher.Mono;

/** Looks a login up by email (any case); the principal's name is the stored email. */
@Service
class UserAccountDetailsService implements ReactiveUserDetailsService {

	private final UserAccountRepository accounts;

	UserAccountDetailsService(UserAccountRepository accounts) {
		this.accounts = accounts;
	}

	@Override
	public Mono<UserDetails> findByUsername(String email) {
		return accounts.findByEmailIgnoringCase(email)
				.map(account -> User.withUsername(account.email())
						.password(account.passwordHash())
						.roles(account.role().name())
						.build());
	}
}
