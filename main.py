from flask import app, Flask, render_template, request, redirect, url_for, make_response, session, send_file
import os
import dotenv
import json
import datetime
import random
from base64 import b64encode, b64decode
import uuid
import io

import argon2
from Crypto.Cipher import AES

dotenv.load_dotenv()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

def generate_account_number():
    account_number = str(random.randint(1000000000000000, 9999999999999999))

    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    if generate_argon2_hash(account_number) in vault_data["accounts"].keys():
        generate_account_number()

    return account_number, [account_number[i:i+4] for i in range(0, len(account_number), 4)]

def generate_argon2_hash(input_string):
    hasher = argon2.PasswordHasher()

    # Using the input string as the salt is reasonable secure and makes sense in this context
    hash_value = hasher.hash(input_string, salt=input_string.encode("utf-8"))
    return hash_value.replace(os.getenv("ARGON2_CONFIG"), "")

def validate_argon2_hash(input_string, hash_value):
    hasher = argon2.PasswordHasher()

    if not hash_value.find(os.getenv("ARGON2_CONFIG")):
        hash_value = os.getenv("ARGON2_CONFIG") + hash_value

    try:
        hasher.verify(hash_value, input_string)
        return True
    except:
        return False

def clean_post_data(data, account_hash):
    cleaned_data = []

    user_folder = data["user-folder"]

    data = data["uploads"]

    for post in data:
        postId = post
        post = data[post]
        if post["type"] == "text":
            encrypted_content = b64decode(post["content"])
            nonce = b64decode(post["nonce"])
            key = account_hash[3:35].encode("utf-8") # super duper uber insecure, no bueno

            decrypted_content = AES.new(key, AES.MODE_CTR, nonce=nonce, use_aesni=True).decrypt(encrypted_content)

            cleaned_data.append({
                "postId": postId,
                "type": "text",
                "date": post["date"],
                "content": decrypted_content.decode("utf-8")
            })

        elif post["type"] == "file":
            if post["filename"].split(".")[-2] in ("png", "jpg", "jpeg", "svg"):

                file_path = os.path.join("vault-files", user_folder, post["filename"])

                with open(file_path, "rb") as f:
                    encrypted_content = f.read()

                key = account_hash[3:35].encode("utf-8")

                decrypted_content = AES.new(key, AES.MODE_CTR, nonce=b64decode(post["nonce"]), use_aesni=True).decrypt(encrypted_content)

                cleaned_data.append({
                    "postId": postId,
                    "type": "file",
                    "date": post["date"],
                    "filename": post["filename"],
                    "content": b64encode(decrypted_content).decode("utf-8")
                })

            else:
                cleaned_data.append({
                    "postId": postId,
                    "type": "file",
                    "date": post["date"],
                    "filename": post["filename"]
                })

    # Most recent entires first
    cleaned_data = cleaned_data[::-1]

    return cleaned_data
    

@app.route("/")
def index():
    return redirect(url_for("vault"))

@app.route("/download", methods=["GET"])
def download():
    account_hash = session["account_number_hash"]

    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    try:
        session["account_number_hash"] in vault_data["accounts"].keys()
    except KeyError:
        return make_response(redirect(url_for("auth")))
    
    if request.args.get("postId") == None:
        return make_response(redirect(url_for("vault")))
    
    postId = request.args.get("postId")

    user_data = vault_data["accounts"][session["account_number_hash"]]

    post = user_data["uploads"][postId]

    if post["type"] == "file":
        file_path = os.path.join("vault-files", user_data["user-folder"], post["filename"])

        with open(file_path, "rb") as f:
            encrypted_content = f.read()

        key = account_hash[3:35].encode("utf-8")

        decrypted_content = AES.new(key, AES.MODE_CTR, nonce=b64decode(post["nonce"]), use_aesni=True).decrypt(encrypted_content)

        file = io.BytesIO(decrypted_content)

        return send_file(file, as_attachment=True, download_name=post["filename"][0:-4])
    
    else:
        return make_response(redirect(url_for("vault")))
    
@app.route("/transparency")
def transparency():

    return render_template("transparency.html")

@app.route("/register")
def register():
    # TODO: Remove comment block
    # with open("vault.json", "r") as f:
    #     vault_data = json.load(f)

    # try:
    #     if session["account_number_hash"] in vault_data["accounts"].keys():
    #         return make_response(redirect(url_for("vault")))
    # except KeyError:
    #     pass

    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register_post():
    account_number, account_number_parts = generate_account_number()
    user_folder = str(uuid.uuid4())

    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    account_number_hash = generate_argon2_hash(account_number)
    vault_data["accounts"][account_number_hash] = {
        "user-folder": user_folder,
        "uploads": {}
    }

    os.mkdir(os.path.join("vault-files", user_folder))

    with open("vault.json", "w") as f:
        json.dump(vault_data, f, indent=4)

    return {"status": "success", "account_number": "<span class='noselect'> - </span>".join(account_number_parts)}

@app.route("/auth", methods=["GET"]) 
def auth():
    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    try:
        if session["account_number_hash"]:
            session.clear()
            return make_response(redirect(url_for("vault")))
    except KeyError:
        pass

    return render_template("auth.html")

@app.route("/auth", methods=["POST"])
def auth_post():
    account_number = request.form.get("account_number")

    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    account_number_hash = generate_argon2_hash(account_number)
    if account_number_hash in vault_data["accounts"].keys():
        session["account_number_hash"] = account_number_hash
        return make_response(redirect(url_for("vault")))
    
    return render_template("auth.html", authFailed=True)

@app.route("/vault", methods=["GET"])
def vault():
    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    try:
        if session["account_number_hash"] in vault_data["accounts"].keys():
            pass
    except:
        return make_response(redirect(url_for("auth")))
    
    return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]), user_folder=vault_data["accounts"][session["account_number_hash"]]["user-folder"])
    
@app.route("/vault", methods=["POST"])
def vault_post():
    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    try:
        if session["account_number_hash"] in vault_data["accounts"].keys():
            pass
        else:
            return make_response(redirect(url_for("auth")))
    except:
        return make_response(redirect(url_for("auth")))
    
    user_data = vault_data["accounts"][session["account_number_hash"]]

    if request.form.get("post-type") == "1":
        content = request.form.get("text-content")

        if content == "":
            return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]), user_folder=vault_data["accounts"][session["account_number_hash"]]["user-folder"])
        
        if not user_data["uploads"]:
            postId = 1
        else:
            postId = int(max(user_data["uploads"].keys(), key=int)) + 1

        key = session["account_number_hash"][3:35].encode("utf-8")

        cipher = AES.new(key, AES.MODE_CTR, use_aesni=True)
        encrypted_content = cipher.encrypt(content.encode("utf-8"))

        vault_data["accounts"][session["account_number_hash"]]["uploads"][postId] = {
            "type": "text",
            "content": b64encode(encrypted_content).decode("utf-8"),
            "nonce": b64encode(cipher.nonce).decode("utf-8"),
            "date": datetime.datetime.now().strftime("%B %d, %Y %#I:%M %p")
        }

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]), user_folder=vault_data["accounts"][session["account_number_hash"]]["user-folder"])
    
    elif request.form.get("post-type") == "2":
        file = request.files["file-content"]

        if file.filename == "":
            return render_template("vault.html", post_data=vault_data["accounts"][session["account_number_hash"]]["uploads"])
        
        file.filename = file.filename + ".bin"
        
        key = session["account_number_hash"][3:35].encode("utf-8")

        cipher = AES.new(key, AES.MODE_CTR, use_aesni=True)
        encrypted_content = cipher.encrypt(file.read())

        if not user_data["uploads"]:
            postId = 1
        else:
            postId = int(max(user_data["uploads"].keys(), key=int)) + 1

        vault_data["accounts"][session["account_number_hash"]]["uploads"][postId] = {
            "type": "file",
            "filename": file.filename,
            "nonce": b64encode(cipher.nonce).decode("utf-8"),
            "date": datetime.datetime.now().strftime("%B %d, %Y %#I:%M %p")
        }

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        with open(os.path.join("vault-files", user_data["user-folder"], file.filename), "wb") as f:
            f.write(encrypted_content)

        return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]), user_folder=vault_data["accounts"][session["account_number_hash"]]["user-folder"])

@app.route("/vault", methods=["DELETE"])
def vault_delete():
    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    try:
        if session["account_number_hash"] in vault_data["accounts"].keys():

            postId = request.json["postId"]

            if vault_data["accounts"][session["account_number_hash"]]["uploads"][postId]["type"] == "file":
                file_path = os.path.join("vault-files", vault_data["accounts"][session["account_number_hash"]]["user-folder"], vault_data["accounts"][session["account_number_hash"]]["uploads"][postId]["filename"])
                os.remove(file_path)

            vault_data["accounts"][session["account_number_hash"]]["uploads"].pop(postId)

            with open("vault.json", "w") as f:
                json.dump(vault_data, f, indent=4)

            return {"status": "success"}

        else:
            return {"status": "error", "error": "user not registered"}
    
    except KeyError as e:
        return {"status": "error", "error": "user not registered"}

@app.route("/vault", methods=["PUT"])
def vault_put():
    with open("vault.json", "r") as f:
            vault_data = json.load(f)

    if session["account_number_hash"] in vault_data["accounts"].keys():

        postId = request.json["postId"]

        if vault_data["accounts"][session["account_number_hash"]]["uploads"][postId]["type"] == "text":
            content = request.json["content"]

            key = session["account_number_hash"][3:35].encode("utf-8")

            cipher = AES.new(key, AES.MODE_CTR, use_aesni=True)
            encrypted_content = cipher.encrypt(content.encode("utf-8"))

            vault_data["accounts"][session["account_number_hash"]]["uploads"][postId]["content"] = b64encode(encrypted_content).decode("utf-8")
            vault_data["accounts"][session["account_number_hash"]]["uploads"][postId]["nonce"] = b64encode(cipher.nonce).decode("utf-8")

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        return {"status": "success"}

if __name__ == "__main__":
    app.run(port=5000)