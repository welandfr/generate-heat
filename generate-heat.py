import os, shutil
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
mail_subject = os.environ.get("MAIL_SUBJECT", "Your server is ready!")
project_number = os.environ.get("PROJECT")

current_date = datetime.now().isoformat('_').split('.')[0]
users = [u.strip() for u in userlist.split(',')]
heat = { 
    'heat_template_version': "2016-10-14",
    'description': f"Stack template {current_date}",
    'resources': {}
}

for user in users:

    user_mail = f'{user}@{default_maildomain}'
    if '@' in user:
        user_mail = user

    # Generate the script that will run on each instance after creation
    user_data = [
        "#!/bin/bash",
        "PASS=$(openssl rand -hex 6)", # Create a password
        "PORT=22$(hostname -I | tail -c 4)", # Get login port for gateway (22 + last two digits of local IP)
        f'useradd -m -s /bin/bash -G sudo {user}', # Create a user with shell, home and sudo
        f'echo "{user}:$PASS" | chpasswd', # Set password
        #f'passwd --expire {user}', # User must change password on first login
        "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config", # Allow password login
        "service sshd restart", # Restart SSH server
        f"""MAIL='{{\
            "to": "{user_mail}", \
            "subject": "{mail_subject}", \
            "body": "Gateway IP: {gateway_ip}<br>\
                SSH Port: '${{PORT}}' <br>\
                login: {user} <br>\
                password: '${{PASS}}'<br>"}}'""", # Create mail 
        f'curl -X POST -H "Content-Type: application/json" -d "$MAIL" {mailer_url}', # Send mail using external API
        '' # <== don't remove this or the LiteralScalarString magic won't work
    ]

    heat["resources"][user] = {
        'type': "OS::Nova::Server",
        'properties': {
            'networks': [{ 'network': f'project_{project_number}'}],
            'key_name': main_ssh_keypair,
            'image': "Ubuntu-22.04",
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


