package com.trans.mcp.model;

import com.fasterxml.jackson.annotation.JsonProperty;

public record CreditResult(
		String userId,
		@JsonProperty("credit_qualified") boolean creditQualified,
		@JsonProperty("risk_level") String riskLevel
) {
}
