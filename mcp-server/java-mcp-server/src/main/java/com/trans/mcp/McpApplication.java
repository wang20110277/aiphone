package com.trans.mcp;

import com.trans.mcp.service.CreditService;
import com.trans.mcp.service.UserService;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class McpApplication {

	public static void main(String[] args) {
		SpringApplication.run(McpApplication.class, args);
	}

	@Bean
	public ToolCallbackProvider userCenterTools(UserService userService, CreditService creditService) {
		return MethodToolCallbackProvider.builder()
				.toolObjects(userService, creditService)
				.build();
	}
}
