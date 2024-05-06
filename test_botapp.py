import subprocess
import os
import sys
import time
import random
import string
import json

def announce(message):
    print("++++++++++++++++++++++++++++++++++++++")
    print("")
    print(message)
    print("")
    print("++++++++++++++++++++++++++++++++++++++")

def execute_command(command):
    try:
        subprocess.run(command, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        cleanup(e.returncode, command)

def execute_command_with_attempts(command, action):
    max_retries = 3
    retry_interval = 10
    retries = 0

    while retries < max_retries:
        retries += 1

        print(f"Attempt {retries}: {action}")
        try:
            subprocess.run(command, check=True, shell=True)
            print(f"{action} successful")
            return
        except subprocess.CalledProcessError:
            print(f"{action} attempt failed")
            if action == "Load BotApp.yml":
                subprocess.run("podman exec --interactive conjur_client conjur policy replace -b root -f policy/DelBotApp.yml", check=True, shell=True)
            time.sleep(retry_interval)

    print(f"Maximum retries reached. Failed to {action}.")
    cleanup(1, "{action}")

announce("UNIT 2. Define Policy")

admin_api_key = subprocess.check_output(["awk", "/API key for admin/{print $NF}", "admin_data"]).decode().strip()
command = f"podman exec --interactive conjur_client conjur login -i admin -p {admin_api_key}"
execute_command_with_attempts(command,"Login as admin")

subprocess.run("podman exec --interactive conjur_client conjur policy replace -b root -f policy/DelBotApp.yml", check=True, shell=True)
command = "podman-compose exec -T client conjur policy load -b root -f policy/BotApp.yml > my_app_data"
execute_command_with_attempts(command, "Load BotApp.yml")
print("")

execute_command("podman-compose exec -T client conjur logout")
print("")

announce("UNIT 3. Store a Secret in Conjur")

file_path = 'my_app_data'
with open(file_path, 'r') as file:
    json_data = file.read()
data = json.loads(json_data)

dave_api_key = [role['api_key'] for role in data['created_roles'].values()][1]
execute_command(f"podman-compose exec -T client conjur login -i Dave@BotApp -p {dave_api_key}")
print("")

secret_val = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
print("Step 2: Generate Secret")
print("")

execute_command(f"podman-compose exec -T client conjur variable set -i BotApp/secretVar -v {secret_val}")
print("")

announce("UNIT 4. Run the Demo App")

bot_api_key = [role['api_key'] for role in data['created_roles'].values()][0]
execute_command(f"podman-compose exec -T bot_app bash -c \"curl -d '{bot_api_key}' -k https://proxy/authn/myConjurAccount/host%2FBotApp%2FmyDemoApp/authenticate > /tmp/conjur_token\"")
print("")

fetched = subprocess.check_output(["podman-compose", "exec", "-T", "bot_app", "bash", "-c", "/tmp/program.sh"]).decode().strip()
print("Step 3: Fetch Secret")
print("")

print("Step 4: Compare Generated and Fetched Secrets")
print(f"Generated:\t{secret_val}")
print(f"Fetched:\t{fetched.split(':')[-1].strip()}")
if secret_val == fetched.split(':')[-1].strip():
    print("Generated secret matches secret fetched by Bot App")
    print("WORKFLOW PASSED.")
else:
    print("Generated secret does not match the secret fetched by Bot App")
    sys.exit(1)
