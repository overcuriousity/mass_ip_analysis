import subprocess
import logging
import ipaddress
import time
import random

def get_whois_servers():
    return ['whois.ripe.net', 'whois.arin.net', 'whois.apnic.net']

def rotate_servers(servers, last_server):
    if last_server in servers:
        servers.remove(last_server)
    return random.choice(servers), servers

def execute_command(ip, command_flag=None, max_retries=10, initial_delay=0.1):
    retries = 0
    delay = initial_delay
    last_server = None
    servers = get_whois_servers()

    while retries < max_retries:
        whois_server, servers = rotate_servers(servers, last_server)
        last_server = whois_server
        command = f'whois -h {whois_server} {command_flag} {ip}' if command_flag else f'whois -h {whois_server} {ip}'
        logging.debug(f'Attempt {retries+1} with {whois_server}: Executing command: {command}')

        try:
            result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
            output = result.decode('utf-8').strip()

            if 'BLOCK' in output:
                logging.debug("BLOCK found in output, attempting retry with a different server")
                raise ValueError("BLOCK found in output")

            return True, output

        except (subprocess.CalledProcessError, ValueError) as e:
            logging.debug(f"Error or BLOCK detected: {e}. Retrying after {delay} seconds.")
            retries += 1
            time.sleep(delay)
            delay *= 1.1  # Adjusted backoff factor

    return False, "Command failed after retries or BLOCK found in all attempts"

def parse_owner_info(whois_output):
    relevant_descriptors = ['netname', 'country', 'owner', 'OrgName', 'org-name']
    owner_lines = []
    for line in whois_output.split('\n'):
        if any(desc in line for desc in relevant_descriptors) and not any(marker in line for marker in ['#', 'Comment:', '%']):
            parts = line.split(':')
            if len(parts) >= 2:
                # Strip whitespace from each part and rejoin
                cleaned_line = ':'.join(part.strip() for part in parts)
                owner_lines.append(cleaned_line)
    return '\n'.join(owner_lines) if owner_lines else "No owner information found"


def run(ip, command_flag=None):
    ip_obj = ipaddress.ip_address(ip)
    if ip_obj.is_global:
        logging.debug(f'Starting WHOIS lookup for {ip}')

        success, output = execute_command(ip, command_flag)
        if success:
            owner_info = parse_owner_info(output).strip()
        else:
            owner_info = output  # Here, the output is an error message
        logging.debug(f'WHOIS lookup result: {owner_info}')

        return {'success': success, 'result': owner_info}
    else:
        return {'success': True, 'result': f"{ip} is in a private address range, skipped"}

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_ip = "8.8.8.8"
    result = run(test_ip)
    print(result)

