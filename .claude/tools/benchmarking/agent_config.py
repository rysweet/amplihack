"""Agent and task configuration loading."""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    """Agent configuration loaded from agent directory."""

    name: str
    agent_dir: Path
    required_env_vars: list[str]
    optional_env_vars: list[str]
    install_dockerfile: str
    command_template: str
    command_template_continue: Optional[str]
    local_source_path: Optional[Path]
    description: str

    @staticmethod
    def from_directory(agent_dir: Path) -> 'AgentConfig':
        """
        Load agent configuration from directory.

        Args:
            agent_dir: Path to agent directory (e.g., data/agents/claude_code/)

        Returns:
            AgentConfig: Parsed configuration

        Raises:
            FileNotFoundError: If required files missing
            ValueError: If configuration invalid
            yaml.YAMLError: If agent.yaml malformed
        """
        if not agent_dir.is_dir():
            raise FileNotFoundError(f"Agent directory not found: {agent_dir}")

        # Check required files
        agent_yaml = agent_dir / "agent.yaml"
        if not agent_yaml.exists():
            raise FileNotFoundError(f"Required file not found: agent.yaml in {agent_dir}")

        install_dockerfile = agent_dir / "install.dockerfile"
        if not install_dockerfile.exists():
            raise FileNotFoundError(f"Required file not found: install.dockerfile in {agent_dir}")

        command_template_file = agent_dir / "command_template.txt"
        if not command_template_file.exists():
            raise FileNotFoundError(f"Required file not found: command_template.txt in {agent_dir}")

        # Parse agent.yaml
        with open(agent_yaml) as f:
            yaml_data = yaml.safe_load(f)

        required_env_vars = yaml_data.get("required_env_vars", [])
        optional_env_vars = yaml_data.get("optional_env_vars", [])
        local_source_path_str = yaml_data.get("local_source_path")
        local_source_path = Path(local_source_path_str) if local_source_path_str else None
        description = yaml_data.get("description", "")

        # Read file contents
        install_dockerfile_content = install_dockerfile.read_text()
        command_template_content = command_template_file.read_text()

        # Check for optional continue template
        command_template_continue_file = agent_dir / "command_template_continue.txt"
        command_template_continue = None
        if command_template_continue_file.exists():
            command_template_continue = command_template_continue_file.read_text()

        # Extract agent name from directory
        agent_name = agent_dir.name

        return AgentConfig(
            name=agent_name,
            agent_dir=agent_dir,
            required_env_vars=required_env_vars,
            optional_env_vars=optional_env_vars,
            install_dockerfile=install_dockerfile_content,
            command_template=command_template_content,
            command_template_continue=command_template_continue,
            local_source_path=local_source_path,
            description=description
        )

    def validate(self) -> bool:
        """
        Validate configuration completeness.

        Returns:
            True if configuration valid

        Raises:
            ValueError: If validation fails with specific reason
        """
        # Check required_env_vars is a list (can be empty)
        if not isinstance(self.required_env_vars, list):
            raise ValueError("required_env_vars must be a list")

        # Check install_dockerfile is non-empty
        if not self.install_dockerfile or not self.install_dockerfile.strip():
            raise ValueError("install_dockerfile cannot be empty")

        # Check command_template contains {{task_instructions}}
        if "{{task_instructions}}" not in self.command_template:
            raise ValueError("command_template must contain {{task_instructions}} placeholder")

        # Validate local_source_path if set
        if self.local_source_path:
            if not self.local_source_path.exists():
                raise ValueError(f"local_source_path does not exist: {self.local_source_path}")
            if not self.local_source_path.is_dir():
                raise ValueError(f"local_source_path is not a directory: {self.local_source_path}")

        return True

    def render_command(self, task_instructions: str) -> str:
        """
        Render command template with task instructions.

        Args:
            task_instructions: Task description to inject

        Returns:
            str: Rendered command ready for execution

        Raises:
            ValueError: If template rendering fails
        """
        # Escape single quotes in task instructions for shell safety
        # Replace ' with '\'' (end quote, escaped quote, start quote)
        escaped_instructions = task_instructions.replace("'", "'\\''")

        # Simple string replacement (more sophisticated templating could use Jinja2)
        rendered = self.command_template.replace("{{task_instructions}}", escaped_instructions)

        return rendered

    def get_all_required_vars(self, task_vars: list[str]) -> list[str]:
        """
        Merge agent and task required environment variables.

        Args:
            task_vars: Required vars from task configuration

        Returns:
            list: Deduplicated list of all required vars
        """
        # Use set to deduplicate, then convert back to list
        all_vars = set(self.required_env_vars + task_vars)
        return list(all_vars)


@dataclass
class TaskConfig:
    """Task configuration loaded from task directory."""

    name: str
    task_dir: Path
    required_env_vars: list[str]
    timeout_seconds: int
    test_command: str
    instructions: str
    description: str
    difficulty: str  # "easy", "medium", "hard"
    is_non_deterministic: bool

    @staticmethod
    def from_directory(task_dir: Path) -> 'TaskConfig':
        """
        Load task configuration from directory.

        Args:
            task_dir: Path to task directory (e.g., data/tasks/arxiv_summarizer/)

        Returns:
            TaskConfig: Parsed configuration

        Raises:
            FileNotFoundError: If required files missing
            ValueError: If configuration invalid
        """
        if not task_dir.is_dir():
            raise FileNotFoundError(f"Task directory not found: {task_dir}")

        # Check required files
        task_yaml = task_dir / "task.yaml"
        if not task_yaml.exists():
            raise FileNotFoundError(f"Required file not found: task.yaml in {task_dir}")

        instructions_file = task_dir / "instructions.txt"
        if not instructions_file.exists():
            raise FileNotFoundError(f"Required file not found: instructions.txt in {task_dir}")

        # Parse task.yaml
        with open(task_yaml) as f:
            yaml_data = yaml.safe_load(f)

        name = yaml_data.get("name", task_dir.name)
        required_env_vars = yaml_data.get("required_env_vars", [])
        timeout_seconds = yaml_data.get("timeout_seconds", 600)
        test_command = yaml_data.get("test_command", "")
        description = yaml_data.get("description", "")

        # Extract task_info
        task_info = yaml_data.get("task_info", {})
        difficulty = task_info.get("difficulty", "medium")
        is_non_deterministic = task_info.get("is_non_deterministic", False)

        # Read instructions
        instructions = instructions_file.read_text()

        return TaskConfig(
            name=name,
            task_dir=task_dir,
            required_env_vars=required_env_vars,
            timeout_seconds=timeout_seconds,
            test_command=test_command,
            instructions=instructions,
            description=description,
            difficulty=difficulty,
            is_non_deterministic=is_non_deterministic
        )

    def validate(self) -> bool:
        """
        Validate task configuration.

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        if not self.name:
            raise ValueError("Task name cannot be empty")

        if not self.test_command:
            raise ValueError("test_command cannot be empty")

        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if not self.instructions or not self.instructions.strip():
            raise ValueError("instructions cannot be empty")

        return True
