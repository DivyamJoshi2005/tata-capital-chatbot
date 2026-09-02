with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

content = content.replace(
    '<option value="qwen2.5:3b">Qwen 2.5 (3B)</option>',
    '<option value="qwen2.5:3b">Qwen 2.5 (3B)</option>\n              <option value="compare_all">⚖️ Compare All Models Live</option>'
)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
