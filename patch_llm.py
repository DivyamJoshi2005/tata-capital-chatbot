with open("llm_client.py", "r") as f:
    content = f.read()

# Add num_ctx to options
content = content.replace(
    '        if temperature is not None:\n            payload["options"] = {"temperature": temperature}',
    '        payload["options"] = {"num_ctx": 2048}\n        if temperature is not None:\n            payload["options"]["temperature"] = temperature'
)

with open("llm_client.py", "w") as f:
    f.write(content)
