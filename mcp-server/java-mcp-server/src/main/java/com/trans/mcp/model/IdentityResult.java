package com.trans.mcp.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record IdentityResult(
		String userId,
		@JsonProperty("name_masked") String nameMasked,
		@JsonProperty("id_last_four") String idLastFour,
		String gender
) {
}
