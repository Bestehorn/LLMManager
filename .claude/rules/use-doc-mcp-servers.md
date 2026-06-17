# Consult the Documentation MCP Servers Before Using External APIs

Before writing or changing code that uses AWS / Bedrock / Strands / AgentCore / CDK
APIs, consult the corresponding MCP documentation server (configured in `.mcp.json`)
rather than relying on memory. API surfaces change; the docs server is authoritative.

Configured servers (auto-approved in `.claude/settings.json`):
- `awslabs.aws-documentation-mcp-server` — AWS service docs (Bedrock, IAM, etc.)
- `strands-agents-mcp-server` — Strands Agents SDK
- `awslabs.amazon-bedrock-agentcore-mcp-server` — Bedrock AgentCore
- `awslabs.cdk-mcp-server` — AWS CDK constructs and guidance

Use them to: confirm a Bedrock Converse API parameter, check model/feature
availability, verify an inference-profile (CRIS) detail, or validate request/response
shapes. Do not guess an API signature — look it up (see `.claude/rules/no-guessing.md`).
