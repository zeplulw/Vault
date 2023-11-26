import os, json
import datetime
from base64 import b64encode
from Crypto.Cipher import AES

_type = input("Enter type: ")

if _type == "text":
    
    content = input("Enter text content: ")
    account_hash = input("Enter account hash: ")
    key = account_hash[3:35].encode("utf-8")

    cipher = AES.new(key, AES.MODE_CTR)
    encrypted_content = cipher.encrypt(content.encode("utf-8"))

    print("----------------")

    print("Encrypted content: " + b64encode(encrypted_content).decode("utf-8"))
    print("Nonce: " + b64encode(cipher.nonce).decode("utf-8"))

    print("----------------\nWritten to database.")

    with open("vault.json", "r") as f:
        data = json.load(f)

    data["accounts"][account_hash]["uploads"][str(len(data["accounts"][account_hash]["uploads"]) + 1)] = {
        "type": "text",
        "content": b64encode(encrypted_content).decode("utf-8"),
        "nonce": b64encode(cipher.nonce).decode("utf-8"),
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    with open("vault.json", "w") as f:
        json.dump(data, f, indent=4)

elif _type == "file":

    content = input("Enter file path: ")
    account_hash = input("Enter account hash: ")
    key = account_hash[3:35].encode("utf-8")

    with open(content, "rb") as f:
        content = f.read()

    cipher = AES.new(key, AES.MODE_CTR)
    encrypted_content = cipher.encrypt(content)

    user_folder = input("Enter user folder path: ")
    output_path = input("Enter output path: ")
    output_path += ".bin"

    with open(f"vault-files\\{user_folder}\\{output_path}", "wb") as f:
        f.write(encrypted_content)

    print("----------------")

    print("Nonce: " + b64encode(cipher.nonce).decode("utf-8"))

    print("----------------\nWritten to user folder.")

    with open("vault.json", "r") as f:
        data = json.load(f)

    user_data = data["accounts"][account_hash]

    if not user_data["uploads"]:
        postId = 1
    else:
        postId = int(max(user_data["uploads"].keys(), key=int)) + 1

    data["accounts"][account_hash]["uploads"][str(postId)] = {
        "type": "file",
        "filename": output_path,
        "nonce": b64encode(cipher.nonce).decode("utf-8"),
        "date": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

    with open("vault.json", "w") as f:
        json.dump(data, f, indent=4)