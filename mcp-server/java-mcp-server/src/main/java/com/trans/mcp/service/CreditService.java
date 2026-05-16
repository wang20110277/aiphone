package com.trans.mcp.service;

import com.trans.mcp.model.CreditResult;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

@Service
public class CreditService {

	@Tool(description = "根据用户ID和手机号哈希查询征信信息，返回是否合格及风险等级，仅 marketing 业务类型使用")
	public CreditResult user_credit_query(
			@ToolParam(description = "用户唯一标识") String user_id,
			@ToolParam(description = "手机号的哈希值") String phone_hash) {
		// TODO: 接入真实征信数据源
		return new CreditResult(
				user_id,
				true,
				"low"
		);
	}
}
