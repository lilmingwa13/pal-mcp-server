"""Claude-specific CLI agent hooks."""

from __future__ import annotations

from clink.models import ResolvedCLIRole
from clink.parsers.base import ParserError

from .base import AgentOutput, BaseCLIAgent
from collections.abc import Sequence

class ClaudeAgent(BaseCLIAgent):
    """Claude CLI agent with system-prompt injection support."""

    def _build_command(
        self,
        *,
        role: ResolvedCLIRole,
        system_prompt: str | None,
        allow_edits: bool = False,
        editable_paths: Sequence[str] = (),
    ) -> list[str]:
        command = list(self.client.executable)
        command.extend(self.client.internal_args)

        config_args = self._sanitize_permission_args(
            self.client.config_args,
            allow_edits=allow_edits,
        )
        command.extend(config_args)

        if system_prompt and "--append-system-prompt" not in config_args:
            command.extend(["--append-system-prompt", system_prompt])

        if allow_edits and editable_paths:
            for path in editable_paths:
                command.extend(["--allowedTools", f"Edit({path})"])
                command.extend(["--allowedTools", f"Write({path})"])

        command.extend(role.role_args)
        return command

    def _recover_from_error(
        self,
        *,
        returncode: int,
        stdout: str,
        stderr: str,
        sanitized_command: list[str],
        duration_seconds: float,
        output_file_content: str | None,
    ) -> AgentOutput | None:
        try:
            parsed = self._parser.parse(stdout, stderr)
        except ParserError:
            return None

        return AgentOutput(
            parsed=parsed,
            sanitized_command=sanitized_command,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration_seconds,
            parser_name=self._parser.name,
            output_file_content=output_file_content,
        )

    def _sanitize_permission_args(self, args: list[str], *, allow_edits: bool) -> list[str]:
        sanitized: list[str] = []
        i = 0

        while i < len(args):
            arg = args[i]

            if arg == "--permission-mode":
                if i + 1 < len(args):
                    mode = args[i + 1]

                    if allow_edits:
                        sanitized.extend([arg, mode])
                    else:
                        sanitized.extend([arg, "default"])

                    i += 2
                    continue

            sanitized.append(arg)
            i += 1

        if "--permission-mode" not in sanitized:
            sanitized.extend([
                "--permission-mode",
                "acceptEdits" if allow_edits else "default",
            ])

        return sanitized