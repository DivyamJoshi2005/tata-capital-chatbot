with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

bad_markup = """<ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-invert prose-sm md:prose-base max-w-none leading-relaxed">
                  {msg.content}
                </ReactMarkdown>"""

good_markup = """<div className="prose prose-invert prose-sm md:prose-base max-w-none leading-relaxed prose-p:my-2 prose-headings:my-3 prose-li:my-1">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>"""

content = content.replace(bad_markup, good_markup)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
