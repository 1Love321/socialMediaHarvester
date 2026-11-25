package com.harvester.socialmediacollector.users;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Clock;

import org.flywaydb.core.api.callback.Callback;
import org.flywaydb.core.api.callback.Context;
import org.flywaydb.core.api.callback.Event;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

/**
 * Creates the first Admin from {@code harvester.first-admin.*} right after Flyway
 * migrates a database that has no user accounts. It runs on Flyway's own JDBC
 * connection during startup migration, so the app stays non-blocking (ADR 0010).
 */
@Component
class FirstAdminSeeder implements Callback {

	private final FirstAdminProperties firstAdmin;
	private final PasswordEncoder passwordEncoder;
	private final Clock clock;

	FirstAdminSeeder(FirstAdminProperties firstAdmin, PasswordEncoder passwordEncoder, Clock clock) {
		this.firstAdmin = firstAdmin;
		this.passwordEncoder = passwordEncoder;
		this.clock = clock;
	}

	@Override
	public boolean supports(Event event, Context context) {
		return event == Event.AFTER_MIGRATE;
	}

	@Override
	public boolean canHandleInTransaction(Event event, Context context) {
		return true;
	}

	@Override
	public void handle(Event event, Context context) {
		try {
			seedIfEmpty(context.getConnection());
		}
		catch (SQLException ex) {
			throw new IllegalStateException("Could not create the first Admin account", ex);
		}
	}

	@Override
	public String getCallbackName() {
		return "first-admin";
	}

	private void seedIfEmpty(Connection connection) throws SQLException {
		try (PreparedStatement any = connection.prepareStatement("SELECT 1 FROM user_account LIMIT 1");
				ResultSet rows = any.executeQuery()) {
			if (rows.next()) {
				return;
			}
		}
		if (!StringUtils.hasText(firstAdmin.email()) || !StringUtils.hasText(firstAdmin.password())) {
			throw new IllegalStateException("The database has no user accounts. Set harvester.first-admin.email and "
					+ "harvester.first-admin.password (e.g. via HARVESTER_FIRST_ADMIN_EMAIL and "
					+ "HARVESTER_FIRST_ADMIN_PASSWORD) so the first Admin can be created.");
		}
		try (PreparedStatement insert = connection.prepareStatement(
				"INSERT INTO user_account (email, password_hash, role, created_at) VALUES (?, ?, 'ADMIN', ?)")) {
			insert.setString(1, firstAdmin.email().trim());
			insert.setString(2, passwordEncoder.encode(firstAdmin.password()));
			insert.setTimestamp(3, Timestamp.from(clock.instant()));
			insert.executeUpdate();
		}
	}
}
