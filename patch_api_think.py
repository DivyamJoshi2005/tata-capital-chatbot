import re

with open("api.py", "r") as f:
    content = f.read()

new_logic = """
        import re
        # Parse `<think>` tags into HTML details tags for the frontend
        def format_think_tags(text):
            pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
            replacement = r'<details className="mb-4 bg-[#1e1e1e] border border-[#333] rounded-lg overflow-hidden"><summary className="bg-[#2a2a2a] px-4 py-2 cursor-pointer text-sm font-semibold text-blue-400 hover:bg-[#333] transition-colors">🧠 View Model Reasoning</summary><div className="p-4 text-xs text-gray-400 italic bg-[#1e1e1e] whitespace-pre-wrap max-h-96 overflow-y-auto">\1</div></details>'
            # Wait, react-markdown + rehype-raw requires standard HTML class attributes
            # So `class="mb-4..."` instead of `className`!
            replacement = r'<details class="mb-4 bg-[#1e1e1e] border border-[#333] rounded-lg overflow-hidden"><summary class="bg-[#2a2a2a] px-4 py-2 cursor-pointer text-sm font-semibold text-blue-400 hover:bg-[#333] transition-colors outline-none select-none">🧠 View Model Reasoning</summary><div class="p-4 text-xs text-gray-400 italic bg-[#1e1e1e] whitespace-pre-wrap max-h-96 overflow-y-auto">\1</div></details>'
            return pattern.sub(replacement, text)

        reply = format_think_tags(reply)
        
        # Add assistant's reply to database
"""

content = content.replace("# Add assistant's reply to database", new_logic.strip())

with open("api.py", "w") as f:
    f.write(content)
