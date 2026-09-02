with open("frontend/tailwind.config.js", "r") as f:
    content = f.read()

content = content.replace("plugins: [],", "plugins: [require('@tailwindcss/typography')],")

with open("frontend/tailwind.config.js", "w") as f:
    f.write(content)
