# app/test_config.py
from app.core.config import settings

print("✅ Endpoint:", settings.azure_openai_endpoint)
print("✅ Key:", settings.azure_openai_api_key[:8] + "..." )  # 避免全显示
print("✅ Deployment:", settings.azure_deployment_name)
print("✅ API Version:", settings.azure_api_version)
