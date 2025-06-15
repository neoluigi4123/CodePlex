"""
Base script to run codeplex.

Changelogs:
- Support over WSL and bash
- Correct Google-style comments

To do list:
- Toggle for sudo commands
- Retry N times when a tool fails
- Fix subprocess started by the model
- Allow argument to set default link and default model
"""
from ollama import Client
import os
import subprocess
import platform

def detect_terminal():
    """Detect the current terminal used.
    
    Returns:
        terminal (str): The terminal being used.
    """
    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC")
    if shell:
        if "bash" in shell:
            if "Windows" in platform.system():
                return "WSL Bash"
            return "Linux Bash"
        else:
            return shell.split(os.sep)[-1]  # fallback to last part of path
    else:
        return None

def detect_linux_distro():
    """Detect the distro of a OS running Linux.

    Returns:
        distro (str): If any distro name found, return it.
    """
    try:
        with open("/etc/os-release") as f:
            lines = f.readlines()
        for line in lines:
            if line.startswith("PRETTY_NAME="):
                return line.strip().split("=")[1].strip('"')
    except FileNotFoundError:
        return None
    return None

OS = platform.system()
TERMINAL = detect_terminal()
DISTRO = detect_linux_distro() if OS == "Linux" else None

print(f"OS: {OS}, Terminal: {TERMINAL}")
if OS == "Windows" and TERMINAL != "WSL Bash":
    print("The program isn't yet supported on Windows. Check documentation to use WSL.")

MODEL = "llama3.1:8b-instruct-q8_0" # "qwen2.5:14b" "qwen3:8b" Use the right model for your compute capacity
LINK = "" #"http://localhost:11434"

ollama_client = Client(
    host=LINK,
)

MODEL_INFO = ollama_client._request_raw("POST", "/api/show",json={"name":MODEL}).json()
MODEL_FAMILY = MODEL_INFO["details"]["family"]
MODEL_CAPABILITIES = MODEL_INFO["capabilities"]
print(f"Model Family: '{MODEL_FAMILY}', Model Capabilities: '{MODEL_CAPABILITIES}'")
if "tools" not in MODEL_CAPABILITIES:
    print(f"{MODEL} doesn't have tools capabilities. Concider using another model from qwen, mistral or llama family.")
    exit()

TOOLS = [
    {
    'type': 'function',
    'function': {
        'name': 'tool_call',
        'description': 'Perform file operations, run CLI commands, or execute Python code locally.',
        'parameters': {
            'type': 'object',
            'properties': {
                'tool': {
                    'type': 'string',
                    'enum': ['file', 'cli', 'python'],
                    'description': 'The tool to use: file for file operations, cli for shell commands, python for executing code.'
                },

                # FILE TOOL
                'action': {
                    'type': 'string',
                    'enum': ['read', 'write', 'delete'],
                    'description': 'File action to perform: read, write or delete. Required if tool = file.'
                },
                'path': {
                    'type': 'string',
                    'description': 'File path for reading, writing or deleting. Required if tool = file.'
                },
                'content': {
                    'type': 'string',
                    'description': 'The content to write to a file. Required if action = write.'
                },

                # CLI TOOL
                'command': {
                    'type': 'string',
                    'description': 'Shell command to run. Required if tool = cli.'
                },
                'expected_output': {
                    'type': 'boolean',
                    'description': 'Set to true if you want the output of the command returned. Optional, defaults to false.'
                },

                # PYTHON TOOL
                'code': {
                    'type': 'string',
                    'description': 'Python code to execute. Required if tool = python.'
                }
            },

            'required': ['tool'],

            'allOf': [
                {
                    'if': {
                        'properties': { 'tool': { 'const': 'file' } }
                    },
                    'then': {
                        'required': ['action', 'path'],
                        'anyOf': [
                            {
                                'properties': { 'action': { 'const': 'write' } },
                                'required': ['content']
                            },
                            {
                                'properties': { 'action': { 'enum': ['read', 'delete'] } }
                            }
                        ]
                    }
                },
                {
                    'if': {
                        'properties': { 'tool': { 'const': 'cli' } }
                    },
                    'then': {
                        'required': ['command']
                    }
                },
                {
                    'if': {
                        'properties': { 'tool': { 'const': 'python' } }
                    },
                    'then': {
                        'required': ['code']
                    }
                }
            ]
        }
    }
}
]

# Tune this pre-prompt to get your own personnal assistant.
SYSTEM_PROMPT = "You are Codeplex, a super powerfull AI assistant. You're currently used in a terminal, so avoid using markdown, hyperlink etc, just ouput raw text. You'll prompt a task to do, then you'll use your tool_calling capabilities to achieve that result. If asked complex task such as math or web browsing, concider using python scripting with libraries such as time or request. Make sure to always go for free and keyless solution. You can manage file, reading, writing, etc."

if TERMINAL == "WSL Bash":
    SYSTEM_PROMPT += f" You're currently running on WSL, meaning that you can use Linux and windows commands."

if TERMINAL == "Linux Bash":
    if DISTRO:
        SYSTEM_PROMPT += f" You're currently running on Linux, {DISTRO}, meaning that you can use Linux commands."
    else:
        SYSTEM_PROMPT += " You're currently running on Linux, meaning that you can use Linux commands."

if "qwen3" in MODEL_FAMILY:
    SYSTEM_PROMPT = f"/no_think\n{SYSTEM_PROMPT}"
    print("Qwen3 isn't supported yet! Please downgrade to qwen2.5 or use another model")
    exit()

context = [{
    'role': 'system',
    'content': SYSTEM_PROMPT
}]

def add_to_context(role,content):
    """Add a message to the context of the model

    Args:
        role (str): The user to set the message from. Can be system, assistant, user or tool_calls.
        content (str): The content of the message.
    """
    context.append({
        'role':role,
        'content':content
    })

def call_file(tool_call):
    """Handles file operations based on the provided tool call.

    Supports reading, writing, and deleting files. The path is expanded to handle 
    user directories and resolved to an absolute path.

    Args:
        tool_call (dict): A dictionary containing the tool call details, including:
            - action (str): The file operation to perform ('read', 'write', 'delete').
            - path (str): The file path to operate on.
            - content (str, optional): Content to write to the file (used for 'write').

    Returns:
        str: 
            - For 'read': The content of the file.
            - For 'write': Success message after writing to the file.
            - For 'delete': Success message after deleting the file.
            - For invalid actions or errors: A descriptive error message.
    """
    args = tool_call['function']['arguments']
    action = args.get('action')
    path = args.get('path')
    content = args.get('content', '')

    # Expand ~ to home directory and resolve relative paths
    if path:
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
    
    try:
        if action == 'read':
            with open(path, 'r') as f:
                result = f.read()
            return result

        elif action == 'write':
            # Create directory if it doesn't exist
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(content)
            return f"Successfully wrote to {path}"

        elif action == 'delete':
            if os.path.exists(path):
                os.remove(path)
                return f"Successfully deleted {path}"
            else:
                error_msg = f"File does not exist: {path}"
                return error_msg

        else:
            error_msg = f"Unknown action: {action}"
            return error_msg

    except Exception as e:
        error_msg = f"File operation error: {e}"
        return error_msg

def call_cli(tool_call):
    """Handles command line operations based on the provided tool call.
    
    Automatically supports the command for the right terminal and os. If path are used,
    it is expanded to handle user directories and resolved to an absolute path.

    Args:
        tool_call (dict): A Dictionary containing the tool call details, including:
            - command (str): The command to execute.
            - expected_output (str, optional): Return the result of the command to the context. Default is True.
    
    Returns:
        str:
            - for "command" the result of the command.
            - for "expected_output" nothing is False.
    """
    args = tool_call['function']['arguments']
    command = args.get('command')
    expect_output = args.get('expected_output', True)
    
    # Expand ~ to full home path
    if isinstance(command, str):
        command = os.path.expanduser(command)
    elif isinstance(command, list):
        command = [os.path.expanduser(arg) if arg.startswith('~') else arg for arg in command]
    
    try:
        if expect_output:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
            return result
        else:
            subprocess.run(command, shell=True)
            return f"Command executed: {command}"
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed: {e.output}"
        return error_msg

def call_python(tool_call):
    """Handles python script based on the provided tool call.
    
    Args:
        tool_call (dict): A dictionary containing the tool call details, including:
            - code (str): The python script to execute.
    
    Returns:
        str:
            - The final variables from the script or an error.
    """
    args = tool_call['function']['arguments']
    code = args.get('code')

    try:
        local_vars = {}
        exec(code, {}, local_vars)
        if local_vars:
            return f"Code executed successfully. Output: {local_vars}"
        else:
            return "Code executed successfully."

    except Exception as e:
        error_msg = f"Python execution error: {e}"
        return error_msg

def get_tool_type(tool_call):
    """Parse tool call to call the correct function.
    
    Args:
        tool_call (dict): A dictionary containing the tool call, including:
            - tool (str): The type of tool to call (file, cli, or python).
    
    Returns:
        str:
            The result of the tool called.
    """
    tool_type = tool_call['function']['arguments'].get('tool')

    if tool_type == 'file':
        return call_file(tool_call)
    elif tool_type == 'cli':
        return call_cli(tool_call)
    elif tool_type == 'python':
        return call_python(tool_call)
    else:
        error_msg = f"Unknown tool type: {tool_type}"
        print(error_msg)
        return error_msg

def generate():
    global context

    while True:
        # Generate reply
        response = ollama_client.chat(
            model=MODEL, 
            messages=context,
            tools=TOOLS,
            options={
                'temperature': 0.15, # Lower value mean more precise response, while higher value mean more creative response.
            })
        
        # Check if response is a direct message
        if response['message'].get('content'):
            add_to_context('assistant', response['message']['content'])
            return response['message']['content']
        
        # Check if response is a tool_calls
        elif 'tool_calls' in response['message']:
            # Loop for each tools in tool_calls
            for tool_call in response['message']['tool_calls']:
                tool_result = get_tool_type(tool_call)
                
                # Add to context
                context.append({
                    'role': 'tool',
                    'content': tool_result,
                    'tool_call_id': tool_call.get('id', 'default')
                })
            
        else:
            return "No response content or tool calls found."

def main():
    while True:
        user_input = input("You: ")
        add_to_context('user', user_input)
        result = generate()
        print(f"Assistant: {result}")

main()
