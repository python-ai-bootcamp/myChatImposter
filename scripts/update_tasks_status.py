import re

path = r"c:\code\myChatImposterProject\myChatImposter_antigravityPlayground\docs\moderateImage_spec_implementationTasks\cursor_unified.md"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

for i in range(1, 16):
    # Update summary table
    content = re.sub(rf"(\| {i} \|.*?\|\s*)PENDING(\s*\|)", rf"\g<1>DONE\g<2>", content)
    # Update section headers
    content = re.sub(rf"(### Task {i} .*?\n\*\*Status:\*\*) PENDING", rf"\1 DONE", content)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Tasks 1 to 15 marked as DONE in cursor_unified.md.")
