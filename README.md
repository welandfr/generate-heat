# Generate OpenStack heat template for orchestrating multiple server instances

### For Linux education on CSC Pouta when you need to spin up separate test servers for each of the course participants

## Install and run
1. Clone the repo
2. Install the dependencies:     
`pip install -r requirements.txt`
3. Create a .env file from the .env-example:    
`cp .env-example .env`
4. Make your changes to the .env file. _Ask me about the API key for the mailer!_
5. Run the script:     
`python3 generate-heat.py`      
The heat template will be saved to `out/heat.yaml`

## How to spin up the servers on OpenStack

For this to work, make sure you have an SSH Gateway server with a floating IP that port-forwards SSH to local IPs. You can create a server instance (tested with the Ubuntu 20.04 image) and use this script to set up port-forwarding: https://github.com/welandfr/IaaS/blob/main/cPouta/teacher/ssh-gateway.sh 

1. Log in to your OpenStack project dashboard on  https://pouta.csc.fi/   
2. Go to Stacks, click Launch Stack
3. Upload the `heat.yaml` you just generated either as a _File_ or copy-and-paste as _Direct input_. Click Next and use your password when asked. (You'll need a separate CSC-account, I don't think Haka will work here)
4. Done! The servers will (ok, should) spin up and the users should get their login info by email.

## Notes

- You can use the _Change Stack Template_ function to upload a new version of the template but __BE AWARE__ that it will delete the current servers in the stack.
