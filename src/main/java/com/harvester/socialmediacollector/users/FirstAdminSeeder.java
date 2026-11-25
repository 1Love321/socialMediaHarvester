package com.harvester.socialmediacollector.users;

import java.time.Clock;
import java.time.Duration;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

/**
 * Creates the first Admin from {@code harvester.first-admin.*} when the database
 * has no user accounts yet; with any account present it does nothing and needs
 * no config. It runs over R2DBC once Flyway has migrated, before the app is
 * reported ready, and fails startup with a clear message when it has to seed
 * but the config is missing.
 */
@Component
class FirstAdminSeeder implements ApplicationRunner {

	private static final Duration STARTUP_TIMEOUT = Duration.ofMinutes(1);

	private final FirstAdminProperties firstAdmin;
	private final PasswordEncoder passwordEncoder;
	private final Clock clock;
	private final UserAccountRepository accounts;

	FirstAdminSeeder(FirstAdminProperties firstAdmin, PasswordEncoder passwordEncoder, Clock clock,
			UserAccountRepository accounts) {
		this.firstAdmin = firstAdmin;
		this.passwordEncoder = passwordEncoder;
		this.clock = clock;
		this.accounts = accounts;
	}

	/**
	 * Waits on the main startup thread, which is not a reactive thread, so
	 * startup cannot finish before the first Admin exists.
	 */
	@Override
	public void run(ApplicationArguments args) {
		seedIfEmpty().block(STARTUP_TIMEOUT);
	}

	Mono<Void> seedIfEmpty() {
		return accounts.count()
				.filter(count -> count == 0)
				.flatMap(none -> newAdmin())
				.flatMap(accounts::save)
				.then();
	}

	private Mono<UserAccount> newAdmin() {
		if (!StringUtils.hasText(firstAdmin.email()) || !StringUtils.hasText(firstAdmin.password())) {
			return Mono.error(new IllegalStateException("The database has no user accounts, so the first Admin "
					+ "must be created, but harvester.first-admin.email or harvester.first-admin.password is missing. "
					+ "Set HARVESTER_FIRST_ADMIN_EMAIL and HARVESTER_FIRST_ADMIN_PASSWORD."));
		}
		// Hashing is slow on purpose, so it stays off the event loop.
		return Mono.fromCallable(() -> new UserAccount(null, firstAdmin.email().trim(),
				passwordEncoder.encode(firstAdmin.password()), Role.ADMIN, clock.instant()))
				.subscribeOn(Schedulers.boundedElastic());
	}
}
