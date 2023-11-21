from flask import app, Flask, render_template, request, redirect, url_for, make_response, session
import os
import dotenv
import json
import time
import datetime
import random
import argon2
import aes
import base64
import uuid

dotenv.load_dotenv()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

def generate_account_number():
    account_number = str(random.randint(1111111111111111, 9999999999999999))

    with open("vault.json", "r") as f:
        vault_data = json.load(f)

    if account_number in vault_data["accounts"].keys():
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
            encrypted_content = base64.b64decode(post["content"])
            iv = base64.b64decode(post["content_iv"])
            key = account_hash[3:19].encode("utf-8") # super duper uber insecure, no bueno

            decrypted_content = aes.AES(key).decrypt_ctr(encrypted_content, iv)

            cleaned_data.append({
                "postId": postId,
                "type": "text",
                "date": post["date"],
                "content": decrypted_content.decode("utf-8")
            })

        elif post["type"] == "file":
            file_path = os.path.join("vault-files", user_folder, post["filename"])

            with open(file_path, "rb") as f:
                encrypted_content = f.read()

            iv = base64.b64decode(post["file_iv"])
            key = account_hash[3:19].encode("utf-8")

            decrypted_content = aes.AES(key).decrypt_ctr(encrypted_content, iv)

            cleaned_data.append({
                "postId": postId,
                "type": "file",
                "date": post["date"],
                "filename": post["filename"],
                "content": base64.b64encode(decrypted_content).decode("utf-8")
            })

    return cleaned_data
    

@app.route("/")
def index():
    return redirect(url_for("vault"))

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
        if session["account_number_hash"] in vault_data["accounts"].keys():
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
            return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]))
        else:
            return make_response(redirect(url_for("auth")))
    except KeyError:
        return make_response(redirect(url_for("auth")))
    
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
            return render_template("vault.html", post_data=vault_data["accounts"][session["account_number_hash"]]["uploads"])
        
        key = session["account_number_hash"][3:19].encode("utf-8")
        iv = os.urandom(16)

        encrypted_content = aes.AES(key).encrypt_ctr(content.encode("utf-8"), iv)

        postId = max(user_data["uploads"].keys(), key=int) + 1

        vault_data["accounts"][session["account_number_hash"]]["uploads"][postId] = {
            "type": "text",
            "content": base64.b64encode(encrypted_content).decode("utf-8"),
            "content_iv": base64.b64encode(iv).decode("utf-8"),
            "date": time.time()
        }

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]))
    
    elif request.form.get("post-type") == "2":
        file = request.files["file-content"]

        if file.filename == "":
            return render_template("vault.html", post_data=vault_data["accounts"][session["account_number_hash"]]["uploads"])
        
        key = session["account_number_hash"][3:19].encode("utf-8")
        iv = os.urandom(16)

        encrypted_content = aes.AES(key).encrypt_ctr(file.read(), iv)

        postId = max(user_data["uploads"].keys(), key=int) + 1

        vault_data["accounts"][session["account_number_hash"]]["uploads"][postId] = {
            "type": "file",
            "filename": file.filename,
            "file_iv": base64.b64encode(iv).decode("utf-8"),
            "date": time.time()
        }

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        with open(os.path.join("vault-files", user_data["user-folder"], postId + "-" + file.filename), "wb") as f:
            f.write(encrypted_content)

        return render_template("vault.html", post_data=clean_post_data(vault_data["accounts"][session["account_number_hash"]], session["account_number_hash"]))

    # if request.cookies.get("authentication") == os.getenv("PERSISTENT_AUTH_SECRET"):
    #     if request.form.get("post-type") == "1":

    #         content = request.form.get("text-content")
            
    #         with open("vault.json", "r") as f:
    #             vault_data = json.load(f)

    #         if content == "":
    #             return render_template("vault.html", post_data=vault_data["accounts"][session["account_number_hash"]]["uploads"])

    #         postId = str(vault_data["currentId"] + 1)

    #         vault_data[postId] = {
    #             "type": "text",
    #             "date": time.time(),
    #             "content": f"{postId}-{content}"
    #         }

    #         vault_data["currentId"] += 1

    #         with open("vault.json", "w") as f:
    #             json.dump(vault_data, f, indent=4)

    #         vault_data.pop("currentId")
    #         return render_template("vault.html", post_data=vault_data["accounts"][session["account_number_hash"]]["uploads"])

    #     elif request.form.get("post-type") == "2":

    #         with open("vault.json", "r") as f:
    #             vault_data = json.load(f)

    #         postId = str(vault_data["currentId"] + 1)


    #         fileNames = []
    #         for file in request.files.getlist("file-content"):

    #             file.save(os.path.join("static/vault-files", f"{postId}-{file.filename}"))

    #             fileNames.append(f"{postId}-{file.filename}")
                
    #         vault_data[postId] = {
    #             "type": "file",
    #             "date": time.time(),
    #             "filename": f"{'|'.join(fileNames)}"
    #         }

    #         vault_data["currentId"] += 1

    #         with open("vault.json", "w") as f:
    #             json.dump(vault_data, f, indent=4)

    #         vault_data.pop("currentId")
    #         return render_template("vault.html", post_data=vault_data["accounts"][session["account_number_hash"]]["uploads"])

    #     else:
    #         return redirect(url_for("vault"))

@app.route("/vault", methods=["DELETE"])
def vault_delete():
    if request.json["authentication"] == os.getenv("PERSISTENT_AUTH_SECRET"):
        with open("vault.json", "r") as f:
            vault_data = json.load(f)

        postId = request.json["postId"]

        if vault_data[postId]["type"] == "file":
            fileList = vault_data[postId]["filename"].split("|")
            
            for file in fileList:
                os.remove(os.path.join("static/vault-files", file))

        vault_data.pop(postId)

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        return {"status": "success"}
    
@app.route("/vault", methods=["PUT"])
def vault_put():
    if request.json["authentication"] == os.getenv("PERSISTENT_AUTH_SECRET"):
        with open("vault.json", "r") as f:
            vault_data = json.load(f)

        postId = request.json["postId"]

        if vault_data[postId]["type"] == "text":
            vault_data[postId]["content"] = f"{postId}-{request.json['content']}"

        with open("vault.json", "w") as f:
            json.dump(vault_data, f, indent=4)

        return {"status": "success"}

if __name__ == "__main__":
    app.run(port=5000)