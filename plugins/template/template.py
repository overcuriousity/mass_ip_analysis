# plugin_name.py


def flatten_output(command):
    """
    Checks the return value of the plugin logic to match the expected file types of the main program. Leave unchanged. 
    """
    try:
        result = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        return True, result.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.decode('utf-8').strip()

def run(entity, command_flag):
    """
    Process an entity and return a result.

    Parameters:
    - entity: The entity to be processed (e.g., an IP address).
    - command_flag: Additional command or configuration passed to the plugin.

    Returns:
    A dictionary containing:
    - 'success': Boolean indicating if the processing was successful.
    - 'result': The processed result or an error message.
    """
    
    try:
        # Plugin-specific logic goes here.
        # For example, if this is an IP address plugin,
        # you might perform an operation like pinging the IP address
        # and return the response time or any other relevant information.

        # Example of processed result (modify according to actual plugin logic)
        processed_result = f"Processed result for {entity} with command flag {command_flag}"

        # Return the result in the standardized format
        return {'success': True, 'result': processed_result}

    except Exception as e:
        # Handle any exceptions and return an error message in the same format
        return {'success': False, 'result': str(e)}
