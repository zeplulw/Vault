import os, aes, base64, json

_type = input("Enter type: ")

if _type == "text":
    
    content = input("Enter text content: ")
    account_hash = input("Enter account hash: ")
    key = account_hash[3:19].encode("utf-8")
    iv = os.urandom(16)

    encrypted_content = aes.AES(key).encrypt_ctr(content.encode("utf-8"), iv)

    print("----------------")

    print("Encrypted content: " + base64.b64encode(encrypted_content).decode("utf-8"))
    print("IV: " + base64.b64encode(iv).decode("utf-8"))

    print("----------------\nWritten to database.")

    with open("vault.json", "r") as f:
        data = json.load(f)

    data["accounts"][account_hash]["uploads"][str(len(data["accounts"][account_hash]["uploads"]) + 1)] = {
        "type": "text",
        "content": base64.b64encode(encrypted_content).decode("utf-8"),
        "content_iv": base64.b64encode(iv).decode("utf-8"),
        "date": "date not implemented"
    }

    with open("vault.json", "w") as f:
        json.dump(data, f, indent=4)

elif _type == "file":

    content = input("Enter file path: ")
    account_hash = input("Enter account hash: ")
    key = account_hash[3:19].encode("utf-8")
    iv = os.urandom(16)

    with open(content, "rb") as f:
        content = f.read()

    encrypted_content = aes.AES(key).encrypt_ctr(content, iv)

    user_folder = input("Enter user folder path: ")
    output_path = input("Enter output path: ")
    output_path += ".bin"

    with open(f"vault-files\\{user_folder}\\{output_path}", "wb") as f:
        f.write(encrypted_content)

    print("Encrypted content: " + base64.b64encode(encrypted_content).decode("utf-8"))
    print("IV: " + base64.b64encode(iv).decode("utf-8"))

    print("----------------\nWritten to user folder.")

    with open("vault.json", "r") as f:
        data = json.load(f)

    data["accounts"][account_hash]["uploads"][max(data["accounts"][account_hash]["uploads"].keys(), key=int)] = {
        "type": "file",
        "filename": output_path,
        "file_iv": base64.b64encode(iv).decode("utf-8"),
        "date": "date not implemented"
    }

    with open("vault.json", "w") as f:
        json.dump(data, f, indent=4)