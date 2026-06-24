# Harness Pipeline Templates for ADK Agent Deployment

Three pipeline templates for deploying ADK agents to managed runtimes, each targeting a different platform and deployment method.

**Template 1: `pipeline_deploy_adk_agent.yaml`** -- Uses **Google Agents CLI** (`agents-cli deploy`) to deploy to GCP Agent Runtime. Single CI stage that validates, tests, deploys source code directly, and manages canary traffic with rollback via the Vertex AI revisions API. Best for projects scaffolded with `agents-cli create`.

**Template 2: `pipeline_deploy_adk_agent_container_image.yaml`** -- Uses **Vertex AI SDK** with the `container_spec` image URI method to deploy to GCP Agent Runtime. Two stages: CI builds and pushes a Docker image to Google Artifact Registry, CD deploys the container via `client.agent_engines.create()`. Includes canary traffic splitting and automatic rollback. Requires `server.py` implementing the BYOC HTTP contract (`/api/reasoning_engine`, `/api/stream_reasoning_engine`).

**Template 3: `pipeline_deploy_adk_agent_aws_agentcore.yaml`** -- Uses **AgentCore CLI** (`agentcore deploy`) to deploy to AWS Bedrock AgentCore Runtime, with **AgentCore Gateway** for traffic management. Two stages: CI validates and tests, CD deploys the agent then uses boto3 to register Gateway targets and create weighted routing rules for canary traffic splitting. Supports automatic promote or rollback based on smoke test results. Requires a pre-existing AgentCore Gateway (pass `gatewayId` variable, or leave empty to skip traffic management).

All templates require platform credentials as Harness secrets. Templates 1 and 2 use `gcp_sa_key_json` + `gcp_region`. Template 3 uses `aws_access_key_id` + `aws_secret_access_key` + `aws_session_token`.
