with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

imports = """import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
"""
content = content.replace("import { useState, useRef, useEffect } from 'react';\nimport ReactMarkdown from 'react-markdown';\nimport remarkGfm from 'remark-gfm';", imports.strip())

content = content.replace(
    "<ReactMarkdown remarkPlugins={[remarkGfm]}>",
    "<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>"
)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
