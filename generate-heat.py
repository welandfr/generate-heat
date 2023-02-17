import os, shutil, subprocess
from datetime import datetime
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import PreservedScalarString, LiteralScalarString
from dotenv import load_dotenv
load_dotenv()

# Set the following in a separate .env file (see .env-example for instaructions)
userlist = os.environ.get("USERLIST") 
default_maildomain = os.environ.get("DEFAULT_MAILDOMAIN")
main_ssh_keypair = os.environ.get("SSH_KEYPAIR") 
mailer_url = os.environ.get("MAILER_URL")
gateway_ip = os.environ.get("GATEWAY_ADDR")
wg_range = os.environ.get("WG_RANGE")

current_date = datetime.now().isoformat('_').split('.')[0]
users = [u.strip() for u in userlist.split(',')]
heat = { 
    'heat_template_version': "2016-10-14",
    'description': f"Stack template {current_date}",
    'resources': {}
}

def wg_genkey():
    privkey = subprocess.check_output("wg genkey", shell=True).decode("utf-8").strip()
    pubkey = subprocess.check_output(f"echo '{privkey}' | wg pubkey", shell=True).decode("utf-8").strip()
    return (privkey, pubkey)

for user in users:

    server_keys = wg_genkey();
    client1_keys = wg_genkey();
    client2_keys = wg_genkey();

    user_mail = f'{user}@{default_maildomain}'
    if '@' in user:
        user_mail = user

    # Generate the script that will run on each instance after creation
    user_data = [
        "#!/bin/bash",
        "OCTET=$(hostname -I | cut -c 11-12)", # Get last two numbers of IP
        "sed -i \"s/<xx>/$OCTET/g\" /etc/wireguard/wg0.conf",
        f"sed -i \"s'<pri>'{server_keys[0]}'g\" /etc/wireguard/wg0.conf", # ' as delimiter because / can exist in string
        f"sed -i \"s'<pub1>'{client1_keys[1]}'g\" /etc/wireguard/wg0.conf",
        f"sed -i \"s'<pub2>'{client2_keys[1]}'g\" /etc/wireguard/wg0.conf",
        "wg-quick down wg0; wg-quick up wg0", # Restart wireguard
        "/opt/genflags.sh; rm /opt/genflags.sh", # Generate flags for CTF (script in server template)
        
        f"""MAIL='{{\
            "to": "{user_mail}", \
            "subject": "Your server is ready!", \
            "body": "Server IP (WireGuard): {wg_range}.'${{OCTET}}'.10<br><br>\
                Client 1 - {wg_range}.'${{OCTET}}'.20<br>\
                Save the following to /etc/wireguard/wg0.conf:<br>\
                <pre>[Interface]<br>\
                Address = {wg_range}.'${{OCTET}}'.20<br>\
                PrivateKey = {client1_keys[0]}<br>\
                DNS = 1.1.1.1<br>\
                <br>\
                [Peer]<br>\
                PublicKey = {server_keys[1]}<br>\
                AllowedIPs = 0.0.0.0/0<br>\
                Endpoint = {gateway_ip}:519'${{OCTET}}'<br>\
                PersistentKeepalive = 25</pre>\
                <br>\
                Client 2 - {wg_range}.'${{OCTET}}'.21<br>\
                Save the following to /etc/wireguard/wg0.conf:<br>\
                <pre>[Interface]<br>\
                Address = {wg_range}.'${{OCTET}}'.21<br>\
                PrivateKey = {client2_keys[0]}<br>\
                DNS = 1.1.1.1<br>\
                <br>\
                [Peer]<br>\
                PublicKey = {server_keys[1]}<br>\
                AllowedIPs = 0.0.0.0/0<br>\
                Endpoint = {gateway_ip}:519'${{OCTET}}'<br>\
                PersistentKeepalive = 25</pre>"}}'""", # Create mail 
                
        f'curl -X POST -H "Content-Type: application/json" -d "$MAIL" {mailer_url}', # Send mail using external API
        'userdel -rf ubuntu', # delete default user
        '' # <== don't remove this or the LiteralScalarString magic won't work
    ]

    heat["resources"][user] = {
        'type': "OS::Nova::Server",
        'properties': {
            'key_name': main_ssh_keypair,
            'image': "vuln-snapshot",
            'flavor': "standard.tiny",
                        # Creates the pipe string block:
            'user_data': LiteralScalarString('\n'.join(user_data)).replace("  ", "")
        }
    }

# Save new heat template
yaml=YAML()
with open('out/heat.yaml', 'w') as f:
    yaml.dump(heat, f)

# Save a copy to archive
shutil.copyfile('out/heat.yaml', f'out/archive/heat-{current_date}.yaml')


