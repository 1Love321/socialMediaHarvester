package com.harvester.socialmediaharvester.model.dto;

import com.harvester.socialmediaharvester.model.Role;
import com.harvester.socialmediaharvester.model.UserAccount;

/** Who is signed in, so the React app can shape itself to the role. */
public record CurrentUserResponse(String email, Role role) {

	public static CurrentUserResponse from(UserAccount account) {
		return new CurrentUserResponse(account.email(), account.role());
	}
}
