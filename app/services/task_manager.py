import asyncio
from typing import Dict, Any, Optional
from enum import Enum

class JobStatus(str, Enum):
    """
    Using Enum prevents spelling mistakes in status strings across the app.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskManager:
    """
    Manages asynchronous background tasks for video processing.
    Bundles the state (active jobs) and behavior (start, get status) together.
    """
    
    def __init__(self):
        # This dictionary represents our "State" (Memory).
        # We store it inside the class instance, not globally in the module.
        # Format: { "video_id": {"status": JobStatus, "progress": 0.0, "queue": asyncio.Queue} }
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, video_id: str) -> None:
        """
        Initializes a new job entry in the manager's memory.
        """
        self._jobs[video_id] = {
            "status": JobStatus.PENDING,
            "progress": 0.0,
            "queue": asyncio.Queue(),  # Queue to pass frames safely between async functions
            "ready_event": asyncio.Event() # Event flag to signal when processing truly starts
        }

    def get_job(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the job dictionary. Returns None if the job doesn't exist.
        The 'Optional' type hint tells the IDE to warn the developer to check for None.
        """
        return self._jobs.get(video_id)

    def update_progress(self, video_id: str, progress: float) -> None:
        """
        Updates the progress of a specific job.
        """
        job = self.get_job(video_id)
        if job:
            job["progress"] = progress

    def set_status(self, video_id: str, status: JobStatus) -> None:
        """
        Updates the status of the job (e.g., from PENDING to PROCESSING).
        """
        job = self.get_job(video_id)
        if job:
            job["status"] = status

    def remove_job(self, video_id: str) -> None:
        """
        Cleans up memory by removing the job once completed or aborted.
        """
        if video_id in self._jobs:
            del self._jobs[video_id]

# Dependency Injection pattern: We create a single instance to be shared.
# Later, if we use Redis, we just change the implementation inside the class, 
# and the rest of the application won't even notice.
task_manager = TaskManager()