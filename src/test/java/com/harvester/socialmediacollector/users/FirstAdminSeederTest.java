package com.harvester.socialmediacollector.users;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;

import com.harvester.socialmediacollector.harness.AppTest;
import com.harvester.socialmediacollector.harness.FirstAdmin;

import reactor.test.StepVerifier;

/** The first Admin is created from config on an empty database only, with the password hashed. */
@AppTest
class FirstAdminSeederTest {

	static final FirstAdminProperties CONFIGURED = new FirstAdminProperties(FirstAdmin.EMAIL, FirstAdmin.PASSWORD);

	@Autowired
	UserAccountRepository accounts;

	@Autowired
	PasswordEncoder passwordEncoder;

	@Autowired
	Clock clock;

	@AfterEach
	void restoreTheFirstAdmin() {
		if (Boolean.FALSE.equals(accounts.findByEmailIgnoringCase(FirstAdmin.EMAIL).hasElement().block())) {
			accounts.deleteAll().then(seeder(CONFIGURED).seedIfEmpty()).block();
		}
	}

	@Test
	void theStoredPasswordIsAHashOfTheConfiguredOne() {
		StepVerifier.create(accounts.findByEmailIgnoringCase(FirstAdmin.EMAIL))
				.assertNext(account -> {
					assertThat(account.passwordHash()).isNotEqualTo(FirstAdmin.PASSWORD)
							.doesNotContain(FirstAdmin.PASSWORD);
					assertThat(passwordEncoder.matches(FirstAdmin.PASSWORD, account.passwordHash())).isTrue();
				})
				.verifyComplete();
	}

	@Test
	void anExistingUserMeansNoSeeding() {
		var someoneElse = new FirstAdminProperties("someone.else@harvester.test", "someone-else-password");

		StepVerifier.create(seeder(someoneElse).seedIfEmpty()).verifyComplete();

		StepVerifier.create(accounts.findByEmailIgnoringCase("someone.else@harvester.test")).verifyComplete();
		StepVerifier.create(accounts.count()).expectNext(1L).verifyComplete();
	}

	@Test
	void anEmptyDatabaseGetsTheConfiguredAdmin() {
		Instant now = clock.instant();

		StepVerifier.create(accounts.deleteAll().then(seeder(CONFIGURED).seedIfEmpty())).verifyComplete();

		StepVerifier.create(accounts.findAll())
				.assertNext(account -> {
					assertThat(account.email()).isEqualTo(FirstAdmin.EMAIL);
					assertThat(account.role()).isEqualTo(Role.ADMIN);
					assertThat(account.createdAt()).isEqualTo(now);
				})
				.verifyComplete();
	}

	@Test
	void anEmptyDatabaseWithoutFirstAdminConfigIsReportedClearly() {
		var missing = new FirstAdminProperties(null, null);

		StepVerifier.create(accounts.deleteAll().then(seeder(missing).seedIfEmpty()))
				.expectErrorSatisfies(error -> assertThat(error)
						.isInstanceOf(IllegalStateException.class)
						.hasMessageContaining("HARVESTER_FIRST_ADMIN_EMAIL")
						.hasMessageContaining("HARVESTER_FIRST_ADMIN_PASSWORD"))
				.verify();
	}

	private FirstAdminSeeder seeder(FirstAdminProperties properties) {
		return new FirstAdminSeeder(properties, passwordEncoder, clock, accounts);
	}
}
