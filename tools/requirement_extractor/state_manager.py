"""
State manager for tracking extraction progress and enabling resume capability
"""
import json
import time
from pathlib import Path
from typing import Optional
from datetime import datetime
from .models import ProcessingState


class StateManager:
    """Manages the state of the extraction process"""

    def __init__(self, state_file: str = ".requirements_extraction_state.json"):
        self.state_file = Path(state_file)
        self.state: Optional[ProcessingState] = None
        self.retry_count = 3
        self.retry_delay = 0.5

    def load_state(self, project_path: str) -> Optional[ProcessingState]:
        """Load existing state or return None if not found"""
        if not self.state_file.exists():
            return None

        try:
            # Retry logic for cloud-synced files
            for attempt in range(self.retry_count):
                try:
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Check if this is for the same project
                    if data.get('project_path') != project_path:
                        return None

                    # Reconstruct ProcessingState
                    state = ProcessingState(
                        project_path=data['project_path'],
                        total_modules=data['total_modules'],
                        processed_modules=data.get('processed_modules', []),
                        failed_modules=data.get('failed_modules', []),
                        current_module=data.get('current_module'),
                        start_time=datetime.fromisoformat(data['start_time']),
                        last_updated=datetime.fromisoformat(data['last_updated']),
                        requirements_file=data.get('requirements_file')
                    )
                    self.state = state
                    return state

                except (OSError, IOError) as e:
                    if attempt < self.retry_count - 1:
                        time.sleep(self.retry_delay)
                        self.retry_delay *= 2
                    else:
                        print(f"Failed to load state after {self.retry_count} attempts: {e}")
                        return None

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Invalid state file: {e}")
            return None

        return None

    def create_state(self, project_path: str, total_modules: int) -> ProcessingState:
        """Create a new processing state"""
        state = ProcessingState(
            project_path=project_path,
            total_modules=total_modules
        )
        self.state = state
        self.save_state()
        return state

    def save_state(self):
        """Save the current state to disk"""
        if not self.state:
            return

        data = {
            'project_path': self.state.project_path,
            'total_modules': self.state.total_modules,
            'processed_modules': self.state.processed_modules,
            'failed_modules': self.state.failed_modules,
            'current_module': self.state.current_module,
            'start_time': self.state.start_time.isoformat(),
            'last_updated': datetime.now().isoformat(),
            'requirements_file': self.state.requirements_file
        }

        # Retry logic for cloud-synced files
        retry_delay = 0.5
        for attempt in range(self.retry_count):
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                    f.flush()
                return

            except (OSError, IOError) as e:
                if attempt < self.retry_count - 1:
                    if attempt == 0:
                        print(f"File I/O error saving state - retrying. "
                              "This may be due to cloud-synced files (OneDrive, Dropbox, etc.).")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"Failed to save state after {self.retry_count} attempts: {e}")
                    raise

    def update_progress(self, module_name: str, success: bool):
        """Update progress for a module"""
        if not self.state:
            return

        if success:
            if module_name not in self.state.processed_modules:
                self.state.processed_modules.append(module_name)
            # Remove from failed if it was there
            if module_name in self.state.failed_modules:
                self.state.failed_modules.remove(module_name)
        else:
            if module_name not in self.state.failed_modules:
                self.state.failed_modules.append(module_name)

        self.state.current_module = None
        self.state.last_updated = datetime.now()
        self.save_state()

    def set_current_module(self, module_name: str):
        """Set the currently processing module"""
        if self.state:
            self.state.current_module = module_name
            self.state.last_updated = datetime.now()
            self.save_state()

    def clear_state(self):
        """Clear the saved state"""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except Exception as e:
                print(f"Failed to clear state file: {e}")
        self.state = None

    def get_remaining_modules(self, all_modules: list[str]) -> list[str]:
        """Get list of modules that still need processing"""
        if not self.state:
            return all_modules

        processed = set(self.state.processed_modules)
        # Optionally include failed modules for retry
        return [m for m in all_modules if m not in processed]