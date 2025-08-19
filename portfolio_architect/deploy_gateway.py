
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient

# Initialize the Gateway client
client = GatewayClient(region_name="us-west-2")

# EZ Auth - automatically sets up Cognito OAuth
cognito_result = client.create_oauth_authorizer_with_cognito("my-gateway")

# create the gateway.
gateway = client.create_mcp_gateway(
    name=None, # the name of the Gateway - if you don't set one, one will be generated.
    role_arn=None, # the role arn that the Gateway will use - if you don't set one, one will be created.
    authorizer_config=cognito_result["authorizer_config"], # the OAuth authorizer details for authorizing callers to your Gateway (MCP only supports OAuth).
    enable_semantic_search=False, # enable semantic search.
)

print(f"MCP Endpoint: {gateway.get_mcp_url()}")
print(f"OAuth Credentials:")
print(f"  Client ID: {cognito_result['client_info']['client_id']}")
print(f"  Scope: {cognito_result['client_info']['scope']}")
