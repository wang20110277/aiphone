package com.trans.mcp.service;

import com.trans.mcp.model.IdentityResult;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

@Service
public class UserService {

	@Tool(description = "根据手机号哈希和业务类型查询用户身份信息，返回脱敏后的姓名、身份证后四位、性别等")
	public IdentityResult user_identity_query(
			@ToolParam(description = "手机号的哈希值，用于脱敏查询") String phone_hash,
			@ToolParam(description = "业务类型：customer_service / collection / marketing") String biz_type) {
		// TODO: 接入真实用户中心数据源
		return new IdentityResult(
				"USER_" + Math.abs(phone_hash.hashCode() % 100000),
				"张**",
				"1234",
				"男"
		);
	}
}
