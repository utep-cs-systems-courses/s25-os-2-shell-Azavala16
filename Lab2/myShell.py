#!/usr/bin/env python3

import os, sys

def run_command(tokens):
    # execute a single external command
    if "/" in tokens[0]:
        program = tokens[0]
        try:
            os.execve(program, tokens, os.environ) # transform a running program into a new unique program
        except Exception:
            print(f"{tokens[0]}: command not found")
            sys.exit(1)
    else:
        for directory in os.environ["PATH"].split(":"):
            program = os.path.join(directory, tokens[0])
            try:
                os.execve(program, tokens, os.environ)
            except FileNotFoundError:
                continue
        print(f"{tokens[0]}: command not found")
        sys.exit(1)

def run_pipeline(command_line, background):
    # executes pipeline of commands which are separated by |
    commands = [cmd.strip() for cmd in command_line.split("|")]
    num_commands = len(commands)
    pids = []
    prev_fd = None

    for i, cmd in enumerate(commands):
        tokens = cmd.split()
        if i < num_commands - 1:
            read_fd, write_fd = os.pipe()
        child_pid = os.fork()   # child process
        if child_pid == 0:      # child successful
            if prev_fd is not None:
                os.dup2(prev_fd, 0)
                os.close(prev_fd)
            if i < num_commands - 1:
                os.dup2(write_fd, 1)
                os.close(read_fd)
                os.close(write_fd)
            run_command(tokens) # handle piped command execution
        else:
            pids.append(child_pid)
            if prev_fd is not None:
                os.close(prev_fd)
            if i < num_commands - 1:
                os.close(write_fd)
                prev_fd = read_fd
    if not background:
        for pid in pids:
            os.waitpid(pid, 0)

def run_redirection(tokens, background):
    # handle input and output redirection
    if ">" in tokens: # handle into
        idx = tokens.index(">")
        cmd_tokens = tokens[:idx]
        filename = tokens[idx + 1]
        child_pid = os.fork()
        if child_pid == 0:
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            os.dup2(fd, 1)
            os.close(fd)
            run_command(cmd_tokens)
        else:
            if not background:
                os.waitpid(child_pid, 0)
        return True
    elif "<" in tokens: # handle from
        idx = tokens.index("<")
        cmd_tokens = tokens[:idx]
        filename = tokens[idx + 1]
        child_pid = os.fork()
        if child_pid == 0:
            fd = os.open(filename, os.O_RDONLY)
            os.dup2(fd, 0)
            os.close(fd)
            run_command(cmd_tokens)
        else:
            if not background:
                os.waitpid(child_pid, 0)
        return True
    return False

def handle_command(command_line):
    # parse and execute a single command line
    command_line = command_line.strip()
    if not command_line:
        return

    tokens = command_line.split()

    
    if tokens[0] == "exit": # if the first cmd is exit
        sys.exit(0)
    if tokens[0] == "cd":   # if it's  change dir
        try:
            os.chdir(tokens[1] if len(tokens) > 1 else os.getenv("HOME")) # if there is no command after cd, go to HOME dir
        except Exception:
            print(f"cd: {tokens[1]}: No such file or directory") # handle invalid command request
        return

    # background execution: remove trailing "&"
    background = False
    if tokens[-1] == "&":
        background = True
        tokens = tokens[:-1]
        command_line = " ".join(tokens)

    # handle pipeline commands (output from a comd as input to the next cmd)
    if "|" in command_line:
        run_pipeline(command_line, background)
        return

    # handle redirection commands 
    if ">" in tokens or "<" in tokens:
        if run_redirection(tokens, background):
            return

    # handle  external command
    child_pid = os.fork()
    if child_pid == 0:
        run_command(tokens)
    else:
        if not background:
            _, status = os.waitpid(child_pid, 0)
            exit_code = os.WEXITSTATUS(status)
            if exit_code != 0:
                print(f"Program terminated with exit code {exit_code}.")

def main():
    while True:
        try:
            # only show prompt if PS1 is non-empty.
            prompt = os.getenv("PS1")
            if prompt is None:
                prompt = "$ "
            command_line = input(prompt)
            # split by newline if given multiple commands.
            for cmd in command_line.split("\n"):
                handle_command(cmd)
        except EOFError:
            # exit on EOF.
            sys.exit(0)

if __name__ == "__main__":
    main()

