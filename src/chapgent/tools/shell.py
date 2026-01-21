import asyncio

from chapgent.tools.base import ToolCategory, ToolRisk, tool

# Output limit to prevent context window overflow
MAX_OUTPUT_SIZE = 30_000  # 30KB


@tool(
    name="shell",
    description="Execute a shell command and return output (truncated if >30KB).",
    risk=ToolRisk.HIGH,
    category=ToolCategory.SHELL,
    cacheable=False,
)
async def shell(command: str, timeout: int = 60) -> str:
    """Execute shell command.

    Args:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Combined stdout and stderr, plus exit code. Large outputs are truncated.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            if process.returncode is None:
                try:
                    process.kill()
                    # Wait for process to actually terminate to avoid zombies
                    await process.wait()
                except ProcessLookupError:
                    pass  # Process already finished
            return f"Error: Command timed out after {timeout} seconds"

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        output = []
        if stdout:
            output.append(stdout)
        if stderr:
            output.append(f"STDERR:\n{stderr}")

        output.append(f"\nExit Code: {process.returncode}")

        result = "\n".join(output).strip()

        # Truncate large outputs to prevent context overflow
        if len(result) > MAX_OUTPUT_SIZE:
            truncated = result[:MAX_OUTPUT_SIZE]
            return (
                f"{truncated}\n\n"
                f"[TRUNCATED: Output was {len(result):,} chars, showing first {MAX_OUTPUT_SIZE:,}. "
                f"Pipe to head/tail or redirect to file for full output.]"
            )

        return result

    except Exception as e:
        return f"Error executing command: {str(e)}"
