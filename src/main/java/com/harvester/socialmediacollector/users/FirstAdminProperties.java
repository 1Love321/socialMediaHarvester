package com.harvester.socialmediacollector.users;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** The Admin created when the database has no user accounts yet. */
@ConfigurationProperties("harvester.first-admin")
public record FirstAdminProperties(String email, String password) {

	@Override
	public String toString() {
		return "FirstAdminProperties[email=" + email + ", password=****]";
	}
}
