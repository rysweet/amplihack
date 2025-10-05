"""
Optimized Session Management for Auto-Mode

High-performance session manager with memory caching, batch operations,
and efficient persistence while preserving all auto-mode requirements.
"""

import asyncio
import json
import time
import os
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict
import weakref
from concurrent.futures import ThreadPoolExecutor
import pickle
import gzip


@dataclass
class OptimizedSessionState:
    """Optimized session state with performance enhancements"""
    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # Conversation context (preserved structure)
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)

    # Analysis state (preserved structure)
    analysis_cycles: int = 0
    analysis_history: List[Any] = field(default_factory=list)
    current_quality_score: float = 0.0

    # Interventions and learning (preserved structure)
    total_interventions: int = 0
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    learned_patterns: List[Dict[str, Any]] = field(default_factory=list)

    # Security and privacy (preserved structure)
    sensitive_data_flags: List[str] = field(default_factory=list)
    permission_grants: Dict[str, bool] = field(default_factory=dict)

    # Performance optimizations
    _dirty: bool = field(default=False, init=False)
    _last_serialized: float = field(default=0.0, init=False)
    _memory_usage: int = field(default=0, init=False)

    def mark_dirty(self):
        """Mark session as needing persistence"""
        self._dirty = True
        self.last_updated = time.time()

    def mark_clean(self):
        """Mark session as persisted"""
        self._dirty = False
        self._last_serialized = time.time()

    @property
    def needs_persistence(self) -> bool:
        """Check if session needs to be persisted"""
        return self._dirty

    def to_dict_optimized(self) -> Dict[str, Any]:
        """Optimized serialization for persistence"""
        state_dict = asdict(self)

        # Optimize analysis_history for serialization
        if self.analysis_history:
            state_dict['analysis_history'] = [
                {
                    'cycle_id': getattr(result, 'cycle_id', ''),
                    'timestamp': getattr(result, 'timestamp', time.time()),
                    'quality_score': getattr(result.analysis, 'quality_score', 0.0) if hasattr(result, 'analysis') else 0.0,
                    'interventions_count': len(getattr(result, 'interventions_suggested', []))
                }
                for result in self.analysis_history[-10:]  # Keep only last 10 for performance
            ]
        else:
            state_dict['analysis_history'] = []

        # Remove performance-related fields
        state_dict.pop('_dirty', None)
        state_dict.pop('_last_serialized', None)
        state_dict.pop('_memory_usage', None)

        return state_dict

    @classmethod
    def from_dict_optimized(cls, data: Dict[str, Any]) -> 'OptimizedSessionState':
        """Optimized deserialization from persistence"""
        # Remove analysis_history for separate handling
        analysis_history_data = data.pop('analysis_history', [])

        # Remove performance fields if present
        data.pop('_dirty', None)
        data.pop('_last_serialized', None)
        data.pop('_memory_usage', None)

        session = cls(**data)

        # Don't restore full analysis_history objects (performance optimization)
        session.analysis_history = []
        session.mark_clean()

        return session


class OptimizedSessionStorage:
    """High-performance session storage with compression and batching"""

    def __init__(self, storage_dir: Optional[str] = None, enable_compression: bool = True):
        """
        Initialize optimized session storage.

        Args:
            storage_dir: Directory for session storage
            enable_compression: Enable gzip compression for stored sessions
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            home = Path.home()
            self.storage_dir = home / '.amplihack' / 'auto-mode' / 'sessions'

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.enable_compression = enable_compression

        # Performance optimizations
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="session_io")
        self._write_queue: asyncio.Queue = asyncio.Queue()
        self._batch_write_task: Optional[asyncio.Task] = None
        self._file_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_times: Dict[str, float] = {}

        # Start batch writer
        self._start_batch_writer()

    def _start_batch_writer(self):
        """Start background batch writer for efficient I/O"""
        if not self._batch_write_task or self._batch_write_task.done():
            self._batch_write_task = asyncio.create_task(self._batch_write_loop())

    async def _batch_write_loop(self):
        """Background loop for batching write operations"""
        write_batch = {}
        last_write = time.time()

        while True:
            try:
                # Wait for writes or timeout
                try:
                    session_id, session_data = await asyncio.wait_for(
                        self._write_queue.get(), timeout=1.0
                    )
                    write_batch[session_id] = session_data
                except asyncio.TimeoutError:
                    pass

                # Write batch if we have data and enough time has passed
                current_time = time.time()
                if write_batch and (
                    len(write_batch) >= 10 or
                    current_time - last_write >= 5.0
                ):
                    await self._flush_write_batch(write_batch)
                    write_batch.clear()
                    last_write = current_time

            except asyncio.CancelledError:
                # Final flush on cancellation
                if write_batch:
                    await self._flush_write_batch(write_batch)
                break
            except Exception as e:
                print(f"Error in batch write loop: {e}")

    async def _flush_write_batch(self, batch: Dict[str, Dict[str, Any]]):
        """Flush a batch of writes to disk"""
        try:
            # Use thread pool for I/O operations
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._thread_pool,
                self._write_batch_sync,
                batch
            )
        except Exception as e:
            print(f"Error flushing write batch: {e}")

    def _write_batch_sync(self, batch: Dict[str, Dict[str, Any]]):
        """Synchronous batch write operation"""
        for session_id, session_data in batch.items():
            try:
                session_file = self._get_session_file(session_id)

                # Prepare data for writing
                if self.enable_compression:
                    serialized = gzip.compress(
                        json.dumps(session_data, separators=(',', ':')).encode('utf-8')
                    )
                    file_suffix = '.json.gz'
                else:
                    serialized = json.dumps(session_data, indent=2).encode('utf-8')
                    file_suffix = '.json'

                # Write atomically using temporary file
                temp_file = session_file.with_suffix(f'{file_suffix}.tmp')
                with open(temp_file, 'wb') as f:
                    f.write(serialized)

                # Atomic move
                final_file = session_file.with_suffix(file_suffix)
                temp_file.rename(final_file)

                # Update cache
                self._file_cache[session_id] = session_data
                self._cache_times[session_id] = time.time()

            except Exception as e:
                print(f"Failed to write session {session_id}: {e}")

    def _get_session_file(self, session_id: str) -> Path:
        """Get optimized file path for session storage"""
        # Use first 2 chars of hash for directory sharding
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        shard_dir = self.storage_dir / session_hash[:2]
        shard_dir.mkdir(exist_ok=True)
        return shard_dir / f"session_{session_hash[2:]}"

    async def save_session_optimized(self, session_state: OptimizedSessionState) -> bool:
        """
        Optimized session save with batching and compression.

        PRESERVES: All session persistence requirements
        OPTIMIZES: I/O batching, compression, and error handling
        """
        try:
            if not session_state.needs_persistence:
                return True  # No changes to persist

            session_data = session_state.to_dict_optimized()

            # Queue for batch writing
            try:
                self._write_queue.put_nowait((session_state.session_id, session_data))
                session_state.mark_clean()
                return True
            except asyncio.QueueFull:
                # Queue is full, write immediately
                return await self._save_session_immediate(session_state)

        except Exception as e:
            print(f"Failed to save session {session_state.session_id}: {e}")
            return False

    async def _save_session_immediate(self, session_state: OptimizedSessionState) -> bool:
        """Immediate session save for critical updates"""
        try:
            session_data = session_state.to_dict_optimized()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._thread_pool,
                self._write_batch_sync,
                {session_state.session_id: session_data}
            )

            session_state.mark_clean()
            return True

        except Exception as e:
            print(f"Failed immediate save for session {session_state.session_id}: {e}")
            return False

    async def load_session_optimized(self, session_id: str) -> Optional[OptimizedSessionState]:
        """
        Optimized session loading with caching.

        PRESERVES: All session loading requirements
        OPTIMIZES: File caching, compression handling, and thread pool I/O
        """
        try:
            # Check cache first
            if session_id in self._file_cache:
                cache_time = self._cache_times.get(session_id, 0)
                if time.time() - cache_time < 300:  # 5-minute cache
                    session_data = self._file_cache[session_id]
                    return OptimizedSessionState.from_dict_optimized(session_data)

            # Load from disk using thread pool
            loop = asyncio.get_event_loop()
            session_data = await loop.run_in_executor(
                self._thread_pool,
                self._load_session_sync,
                session_id
            )

            if session_data:
                return OptimizedSessionState.from_dict_optimized(session_data)

            return None

        except Exception as e:
            print(f"Failed to load session {session_id}: {e}")
            return None

    def _load_session_sync(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Synchronous session loading operation"""
        try:
            session_file = self._get_session_file(session_id)

            # Try compressed file first
            compressed_file = session_file.with_suffix('.json.gz')
            if compressed_file.exists():
                with open(compressed_file, 'rb') as f:
                    compressed_data = f.read()
                    json_data = gzip.decompress(compressed_data).decode('utf-8')
                    session_data = json.loads(json_data)
            else:
                # Try uncompressed file
                uncompressed_file = session_file.with_suffix('.json')
                if uncompressed_file.exists():
                    with open(uncompressed_file, 'r') as f:
                        session_data = json.load(f)
                else:
                    return None

            # Update cache
            self._file_cache[session_id] = session_data
            self._cache_times[session_id] = time.time()

            return session_data

        except Exception as e:
            print(f"Failed to load session {session_id}: {e}")
            return None

    async def delete_session_optimized(self, session_id: str) -> bool:
        """Optimized session deletion"""
        try:
            # Remove from cache
            self._file_cache.pop(session_id, None)
            self._cache_times.pop(session_id, None)

            # Delete files using thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._thread_pool,
                self._delete_session_sync,
                session_id
            )

            return True

        except Exception as e:
            print(f"Failed to delete session {session_id}: {e}")
            return False

    def _delete_session_sync(self, session_id: str):
        """Synchronous session deletion"""
        session_file = self._get_session_file(session_id)

        # Delete both compressed and uncompressed versions
        for suffix in ['.json.gz', '.json']:
            file_path = session_file.with_suffix(suffix)
            if file_path.exists():
                file_path.unlink()

    async def list_sessions_optimized(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Optimized session listing with caching"""
        try:
            loop = asyncio.get_event_loop()
            sessions = await loop.run_in_executor(
                self._thread_pool,
                self._list_sessions_sync,
                user_id
            )
            return sessions

        except Exception as e:
            print(f"Failed to list sessions: {e}")
            return []

    def _list_sessions_sync(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Synchronous session listing"""
        sessions = []

        try:
            # Scan all shard directories
            for shard_dir in self.storage_dir.iterdir():
                if not shard_dir.is_dir():
                    continue

                for session_file in shard_dir.glob("session_*.json*"):
                    try:
                        # Load session metadata only
                        if session_file.suffix == '.gz':
                            with open(session_file, 'rb') as f:
                                compressed_data = f.read()
                                json_data = gzip.decompress(compressed_data).decode('utf-8')
                                session_data = json.loads(json_data)
                        else:
                            with open(session_file, 'r') as f:
                                session_data = json.load(f)

                        # Filter by user_id if specified
                        if user_id and session_data.get('user_id') != user_id:
                            continue

                        # Return metadata only
                        sessions.append({
                            'session_id': session_data['session_id'],
                            'user_id': session_data['user_id'],
                            'created_at': session_data['created_at'],
                            'last_updated': session_data['last_updated'],
                            'analysis_cycles': session_data['analysis_cycles'],
                            'current_quality_score': session_data['current_quality_score']
                        })

                    except Exception as e:
                        print(f"Failed to read session file {session_file}: {e}")
                        continue

        except Exception as e:
            print(f"Failed to list sessions: {e}")

        return sessions

    async def cleanup(self):
        """Cleanup resources and flush pending writes"""
        try:
            # Cancel batch writer and wait for completion
            if self._batch_write_task and not self._batch_write_task.done():
                self._batch_write_task.cancel()
                try:
                    await self._batch_write_task
                except asyncio.CancelledError:
                    pass

            # Shutdown thread pool
            self._thread_pool.shutdown(wait=True)

        except Exception as e:
            print(f"Error during storage cleanup: {e}")


class OptimizedSessionManager:
    """
    High-performance session manager with memory caching and optimized persistence.

    PRESERVES: All auto-mode session management requirements
    OPTIMIZES: Memory usage, I/O batching, and lookup performance
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage = OptimizedSessionStorage(storage_dir)

        # In-memory session cache for active sessions
        self.active_sessions: Dict[str, OptimizedSessionState] = {}
        self.session_index: Dict[str, List[str]] = defaultdict(list)  # user_id -> [session_ids]

        # Performance settings (preserved requirements)
        self.session_timeout_minutes = 60
        self.max_sessions_per_user = 5
        self.cleanup_interval_minutes = 10

        # Optimized cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_sessions_created': 0,
            'total_sessions_cleaned': 0
        }

    async def initialize(self):
        """Initialize the optimized session manager"""
        # Start optimized cleanup task
        self._cleanup_task = asyncio.create_task(self._optimized_cleanup_loop())

    async def create_session_optimized(self, session_id: str, user_id: str,
                                     initial_context: Dict[str, Any]) -> OptimizedSessionState:
        """
        Create optimized session with performance enhancements.

        PRESERVES: All session creation requirements
        OPTIMIZES: Memory indexing and duplicate prevention
        """
        # Check if session already exists (with index lookup)
        if session_id in self.active_sessions:
            raise ValueError(f"Session {session_id} already exists")

        # Optimized user session limit check using index
        user_session_ids = self.session_index[user_id]
        if len(user_session_ids) >= self.max_sessions_per_user:
            # Clean up oldest session using index
            oldest_session_id = min(
                user_session_ids,
                key=lambda sid: self.active_sessions[sid].last_updated
            )
            await self.close_session_optimized(oldest_session_id)

        # Create optimized session state
        session_state = OptimizedSessionState(
            session_id=session_id,
            user_id=user_id,
            conversation_context=initial_context.copy()
        )

        # Store in optimized structures
        self.active_sessions[session_id] = session_state
        self.session_index[user_id].append(session_id)

        # Asynchronous persistence (non-blocking)
        session_state.mark_dirty()
        await self.storage.save_session_optimized(session_state)

        # Update stats
        self._stats['total_sessions_created'] += 1

        return session_state

    async def get_session_optimized(self, session_id: str) -> Optional[OptimizedSessionState]:
        """
        Optimized session retrieval with memory caching.

        PRESERVES: All session retrieval requirements
        OPTIMIZES: Cache-first lookup and lazy loading
        """
        # Check active sessions first (memory cache)
        if session_id in self.active_sessions:
            self._stats['cache_hits'] += 1
            return self.active_sessions[session_id]

        self._stats['cache_misses'] += 1

        # Load from storage and add to cache
        stored_session = await self.storage.load_session_optimized(session_id)
        if stored_session:
            # Add to active sessions cache
            self.active_sessions[session_id] = stored_session
            self.session_index[stored_session.user_id].append(session_id)
            return stored_session

        return None

    async def update_conversation_optimized(self, session_state: OptimizedSessionState,
                                          conversation_update: Dict[str, Any]) -> bool:
        """
        Optimized conversation update with lazy persistence.

        PRESERVES: All conversation update requirements
        OPTIMIZES: Batched updates and dirty tracking
        """
        try:
            # Update conversation context (preserved structure)
            session_state.conversation_context.update(conversation_update)

            # Add to conversation history (preserved structure)
            session_state.conversation_history.append({
                'timestamp': time.time(),
                'update': conversation_update.copy()
            })

            # Optimize conversation history size
            if len(session_state.conversation_history) > 100:
                session_state.conversation_history = session_state.conversation_history[-50:]

            # Mark for lazy persistence
            session_state.mark_dirty()

            # Asynchronous persistence (batched)
            await self.storage.save_session_optimized(session_state)

            return True

        except Exception as e:
            print(f"Failed to update conversation for session {session_state.session_id}: {e}")
            return False

    async def close_session_optimized(self, session_id: str) -> bool:
        """
        Optimized session closure with efficient cleanup.

        PRESERVES: All session closure requirements
        OPTIMIZES: Index maintenance and final persistence
        """
        try:
            if session_id not in self.active_sessions:
                print(f"Attempted to close non-existent session: {session_id}")
                return False

            session_state = self.active_sessions[session_id]

            # Final save if dirty
            if session_state.needs_persistence:
                await self.storage.save_session_optimized(session_state)

            # Remove from optimized structures
            user_id = session_state.user_id
            del self.active_sessions[session_id]

            # Clean up index
            if session_id in self.session_index[user_id]:
                self.session_index[user_id].remove(session_id)

            if not self.session_index[user_id]:
                del self.session_index[user_id]

            return True

        except Exception as e:
            print(f"Failed to close session {session_id}: {e}")
            return False

    async def _optimized_cleanup_loop(self):
        """Optimized cleanup loop with efficient session scanning"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_minutes * 60)

                current_time = time.time()
                timeout_seconds = self.session_timeout_minutes * 60

                # Efficient expired session detection using active sessions only
                expired_sessions = []
                for session_id, session_state in self.active_sessions.items():
                    if current_time - session_state.last_updated > timeout_seconds:
                        expired_sessions.append(session_id)

                # Clean up expired sessions
                cleaned_count = 0
                for session_id in expired_sessions:
                    if await self.close_session_optimized(session_id):
                        cleaned_count += 1

                if cleaned_count > 0:
                    print(f"Cleaned up {cleaned_count} expired auto-mode sessions")
                    self._stats['total_sessions_cleaned'] += cleaned_count

                # Log performance stats periodically
                if self._stats['cache_hits'] + self._stats['cache_misses'] > 0:
                    hit_rate = self._stats['cache_hits'] / (self._stats['cache_hits'] + self._stats['cache_misses'])
                    print(f"Session cache hit rate: {hit_rate:.2%}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in optimized cleanup loop: {e}")

    async def shutdown_optimized(self):
        """Optimized shutdown with efficient resource cleanup"""
        try:
            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Batch save all dirty sessions
            dirty_sessions = [
                session for session in self.active_sessions.values()
                if session.needs_persistence
            ]

            if dirty_sessions:
                print(f"Saving {len(dirty_sessions)} dirty sessions...")
                save_tasks = [
                    self.storage.save_session_optimized(session)
                    for session in dirty_sessions
                ]
                await asyncio.gather(*save_tasks, return_exceptions=True)

            # Cleanup storage
            await self.storage.cleanup()

            # Clear memory structures
            self.active_sessions.clear()
            self.session_index.clear()

            print("Optimized session manager shutdown complete")

        except Exception as e:
            print(f"Error during optimized session manager shutdown: {e}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        total_lookups = self._stats['cache_hits'] + self._stats['cache_misses']
        cache_hit_rate = self._stats['cache_hits'] / total_lookups if total_lookups > 0 else 0.0

        return {
            'active_sessions': len(self.active_sessions),
            'users_with_sessions': len(self.session_index),
            'cache_hit_rate': cache_hit_rate,
            'total_sessions_created': self._stats['total_sessions_created'],
            'total_sessions_cleaned': self._stats['total_sessions_cleaned'],
            'memory_usage_mb': sum(
                len(str(session)) for session in self.active_sessions.values()
            ) / (1024 * 1024)
        }

    def get_user_session_count_optimized(self, user_id: str) -> int:
        """Get optimized user session count using index"""
        return len(self.session_index.get(user_id, []))