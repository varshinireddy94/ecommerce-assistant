from pathlib import Path


POLICY_DIR = Path("policies")


total_words = 0
total_files = 0

print("=" * 60)
print("POLICY CORPUS CHECK")
print("=" * 60)

for file_path in sorted(POLICY_DIR.rglob("*.txt")):

    # Ignore the old policy files in the root of policies/
    if file_path.parent == POLICY_DIR:
        continue

    text = file_path.read_text(encoding="utf-8")

    words = len(text.split())
    characters = len(text)

    total_files += 1
    total_words += words

    print(f"\n{file_path.relative_to(POLICY_DIR)}")
    print(f"Words      : {words}")
    print(f"Characters : {characters}")

print("\n" + "=" * 60)
print(f"TOTAL FILES : {total_files}")
print(f"TOTAL WORDS : {total_words}")
print("=" * 60)