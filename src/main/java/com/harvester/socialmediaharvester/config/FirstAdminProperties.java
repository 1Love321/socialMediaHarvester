package com.harvester.socialmediaharvester.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/**
 * The Admin created when the database has no user accounts yet. Both values may
 * be absent: they are required, and checked, only when seeding is needed.
 */
@Validated
@ConfigurationProperties("harvester.first-admin")
public record FirstAdminProperties(String email, String password) {

	@Override
	public String toString() {
		return "FirstAdminProperties[email=" + email + ", password=****]";
	}
}
