with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

# Add imports
imports = """import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
"""
content = content.replace("import { useState, useRef, useEffect } from 'react';", imports)

# Replace rendering
old_render = "{msg.content}"
new_render = """<ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-invert prose-sm md:prose-base max-w-none leading-relaxed">
                  {msg.content}
                </ReactMarkdown>"""
content = content.replace(old_render, new_render)

# Remove the whitespace-pre-wrap to avoid conflict with typography
content = content.replace("bg-[#262626] text-gray-100 border border-[#333] rounded-2xl rounded-tl-sm shadow-md whitespace-pre-wrap", "bg-[#262626] text-gray-100 border border-[#333] rounded-2xl rounded-tl-sm shadow-md overflow-x-auto")

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
