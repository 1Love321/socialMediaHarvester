package com.harvester.socialmediacollector.users;

import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.repository.reactive.ReactiveCrudRepository;

import reactor.core.publisher.Mono;

public interface UserAccountRepository extends ReactiveCrudRepository<UserAccount, Long> {

	@Query("SELECT * FROM user_account WHERE lower(email) = lower(:email)")
	Mono<UserAccount> findByEmailIgnoringCase(String email);
}
