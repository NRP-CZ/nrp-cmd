"""Progress bar for the command line."""
from __future__ import annotations

import contextlib
import contextvars
from threading import RLock
from typing import TYPE_CHECKING, Any, Protocol, override

from tqdm import tqdm

if TYPE_CHECKING:
    from collections.abc import Generator
    


class DummyLock:
    """A dummy lock that does nothing."""

    def __enter__(self):
        """Enter the lock."""
        yield self
    
    def __exit__(self, *args: Any):
        """Exit the lock."""
        pass


class ProgressBar(Protocol):
    """An abstract interface for a single progress bar."""
    
    def increment(self, progress: int) -> None:
        """Increment the progress by the given value."""
        ...
    
    def set_value(self, progress: int) -> None:
        """Set the progress to the given value."""
        ...
    
    def set_total(self, total_value: int) -> None:
        """Set the total value of the progress."""
        ...

    def finish(self) -> None:
        """Finish the progress."""
        ...

    def increment_total(self, total_increment: int) -> None:
        """Increment the total value of the progress."""
        ...


class Progress(Protocol):
    """A progress that can have multiple sub-progresses.
    
    Some of the sub-processes can be short tasks that do not show a progress bar, 
    but just increase the size of the primary progress bar by 1. 
    
    Some are long tasks that show a separate progress bar.
    
    ```
    p = TQDMProgress()
    
    with p.long_task("Doing something big") as progress:
        p.set_total(100)
        for i in range(100):
            progress.update(1)
            
    with p.short_task() as progress:
        time.sleep(1)
    ```
    
    """

    def increment(self, progress: int) -> None:
        """Increment the progress by the given value."""
        ...
    
    def set_value(self, progress: int) -> None:
        """Set the progress to the given value."""
        ...

    def set_total(self, total_value: int) -> None:
        """Set the total value of the progress."""
        ...

    def increment_total(self, total_increment: int) -> None:
        """Increment the total value of the progress."""
        ...

    @contextlib.contextmanager
    def long_task(self, name: str, increment_total: bool=True) -> Generator[ProgressBar, None, None]:
        """Start a long task with the given name.
        
        The long task will be represented by a tqdm secondary progress bar.
        As this is a context manager, you do not need to call `finish` on the
        returned progress object.
        """
        progress = self.start_long_task(name, increment_total)
        try:
            yield progress
        finally:
            progress.finish()
        
        
    @contextlib.contextmanager
    def short_task(
        self, increment_total: bool = False
    ) -> Generator[ProgressBar, None, None]:
        """Start a short task.
        
        The short task will not show a progress bar,
        instead it will increase the size of the primary progress bar by 1
        and move the one tick when the task is finished.
        """
        progress = self.start_short_task(increment_total)
        try:
            yield progress
        finally:
            progress.finish()

    def start_short_task(self, increment_total: bool = False) -> ProgressBar:
        """Start a short task.
        
        Mostly it is better to use the `short_task` context manager. If you start
        the task manually, you need to call `finish` on the returned progress object.
        """
        ...

    def start_long_task(self, name: str, increment_total: bool = True) -> ProgressBar:
        """Start a long task with the given name.
        
        Mostly it is better to use the `long_task` context manager. If you start
        the task manually, you need to call `finish` on the returned progress object.
        """
        ...
    
    def finish(self) -> None:
        """Finish and remove the progress."""
        pass
    
    
class DummyProgressBar(ProgressBar):
    """A dummy progress bar that does nothing."""
    
    @override
    def increment(self, progress: int) -> None:
        pass
    
    @override
    def set_value(self, progress: int) -> None:
        pass
    
    @override
    def set_total(self, total_value: int) -> None:
        pass

    def increment_total(self, total_increment: int) -> None:
        """Increment the total value of the progress."""
        pass

    @override
    def finish(self) -> None:
        pass
    
    
class DummyProgress(Progress):
    """A dummy progress that does nothing."""

    @override
    def increment(self, progress: int) -> None:
        pass
    
    @override
    def set_value(self, progress: int) -> None:
        pass

    @override
    def set_total(self, total_value: int) -> None:
        pass

    def increment_total(self, total_increment: int) -> None:
        """Increment the total value of the progress."""
        pass

    @override
    def start_short_task(self, increment_total: bool = False) -> ProgressBar:
        return DummyProgressBar()

    @override
    def start_long_task(self, name: str, increment_total: bool = True) -> ProgressBar:
        return DummyProgressBar()

    @override
    def finish(self) -> None:
        pass


class TQDMProgressBar(ProgressBar):
    """A progress bar that uses tqdm to show progress."""
    
    def __init__(self, progress: TQDMProgress, desc: str, position: int = 0):
        """Create a new progress bar."""
        self._progress = progress
        self._position = position
        self.bar = tqdm(total=1, desc=desc, position=position, delay=0, leave=False)
        
    @override
    def increment(self, progress: int) -> None:
        self.bar.update(progress)
        with self.bar.get_lock():
            self._progress.increment(progress)
    
    @override
    def set_value(self, progress: int) -> None:
        with self.bar.get_lock():
            self.increment(progress - self.bar.n)
    
    @override
    def set_total(self, total_value: int) -> None:
        previous_total = self.bar.total
        self.bar.total = total_value
        self.bar.update(0)
        self._progress._change_total(total_value - previous_total)

    def increment_total(self, total_increment: int) -> None:
        """Increment the total value of the progress."""
        self.set_total(self.bar.total + total_increment)

    @override
    def finish(self) -> None:
        self.bar.close()
        self._progress._finish_bar(self._position)            
        
        
class TQDMShortProgressBar(DummyProgressBar):
    """A short progress bar that does not show a progress bar, but just increments the total."""

    def __init__(self, progress: TQDMProgress):
        """Create a new short progress bar."""
        self._progress = progress
        
    @override
    def finish(self) -> None:
        self._progress.increment(1)
        
        
class TQDMProgress(Progress):
    """A progress that uses tqdm to show progress bars.
    
    Note: TQDM is not thread safe, so in synchronous code that can use
    threading to do parallel downloads/uploads, you should set `thread_safe=True`
    to use a `threading.RLock` to protect the tqdm instance.
    """

    def __init__(self, thread_safe: bool=False, total: int=0):
        """Create a new progress."""
        self.lock = DummyLock() if not thread_safe else RLock()
        self.bar = tqdm(total=total, position=0, leave=False)
        # initialize the internal bar's write lock
        self.bar.get_lock()
        self.used_positions: set[int] = set()
        
    @override
    def start_short_task(self, increment_total: bool = False) -> ProgressBar:
        if increment_total:
            self.bar.total += 1
            self.bar.update(0)
        progress = TQDMShortProgressBar(self)
        return progress

    @override
    def start_long_task(self, name: str, increment_total: bool = True) -> ProgressBar:
        if increment_total:
            self.bar.total += 1
            self.bar.update(0)
        progress = TQDMProgressBar(self, name, self._get_unused_position())
        return progress
    
    @override
    def increment(self, progress: int) -> None:
        # this can be called from sub-progresses, so we need to lock
        with self.lock:
            self.bar.update(progress)
    
    @override
    def set_value(self, progress: int) -> None:
        # this can be called from sub-progresses, so we need to lock
        with self.lock:
            self.bar.update(progress - self.bar.n)
    
    @override
    def set_total(self, total_value: int) -> None:
        # this can be called from sub-progresses, so we need to lock
        with self.lock:
            self.bar.total = total_value
            self.bar.update(0)

    def increment_total(self, total_increment: int) -> None:
        """Increment the total value of the progress."""
        self.set_total(self.bar.total + total_increment)

    @override
    def finish(self) -> None:
        """Finish and remove the progress."""
        self.bar.close()

    def _finish_bar(self, position: int) -> None:
        with self.lock:
            self.increment(1)
            self.used_positions.remove(position)

    def _get_unused_position(self) -> int:
        with self.lock:
            i = 1
            while True:
                if i not in self.used_positions:
                    self.used_positions.add(i)
                    return i
                i += 1
                
    def _change_total(self, change: int) -> None:
        with self.lock:
            self.bar.total += change
            self.bar.update(0)

current_progress_container = contextvars.ContextVar[Progress](
    "current_progress", default=DummyProgress()
)


class CurrentProgress(Progress):
    """A progress that uses the current progress object."""

    @override
    def increment(self, progress: int) -> None:
        current_progress_container.get().increment(progress)

    @override
    def set_value(self, progress: int) -> None:
        current_progress_container.get().set_value(progress)

    @override
    def set_total(self, total_value: int) -> None:
        current_progress_container.get().set_total(total_value)

    @override
    def increment_total(self, total_value: int) -> None:
        current_progress_container.get().increment_total(total_value)

    @override
    def start_short_task(self, increment_total: bool = False) -> ProgressBar:
        return current_progress_container.get().start_short_task(increment_total)

    @override
    def start_long_task(self, name: str, increment_total: bool = True) -> ProgressBar:
        return current_progress_container.get().start_long_task(name, increment_total)

    @override
    def finish(self) -> None:
        current_progress_container.get().finish()


current_progress = CurrentProgress()


@contextlib.contextmanager
def show_progress(
    *, impl_class: type[Progress] | None = None, total: int = 0, quiet: bool = False
) -> Generator[Progress]:
    """Create a progress object using the given implementation class."""
    if not impl_class:
        impl_class = DummyProgress if quiet else TQDMProgress
    progress = impl_class()
    token = current_progress_container.set(progress)
    try:
        if total:
            progress.set_total(total)
        yield progress
    finally:
        progress.finish()
        current_progress_container.reset(token)


if __name__ == "__main__":
    import asyncio
    
    async def main() -> None:
        """Just an example of how to use the progress bars."""
        i: int
        
        progress = TQDMProgress()
        progress.set_total(20)
        for _ in range(20):
            progress.increment(1)
            await asyncio.sleep(0.1)
        progress.finish()
    
        progress = TQDMProgress(total=20)
        for _ in range(20):
            with progress.short_task(increment_total=False):
                await asyncio.sleep(0.1)
        progress.finish()
    
        progress = TQDMProgress()
        progress.set_total(10)
        for i in range(10):
            with progress.long_task(f"Task {i}", increment_total=False) as long_progress:
                long_progress.set_total(10)
                for _ in range(10):
                    long_progress.increment(1)
                    await asyncio.sleep(0.1)
        progress.finish()

        progress = TQDMProgress()
        async with asyncio.TaskGroup() as progress_group:
            for i in range(10):
                async def worker(i: int) -> None:
                    with progress.long_task(f"Task {i}") as long_progress:
                        long_progress.set_total(20)
                        for _ in range(20):
                            long_progress.increment(1)
                            await asyncio.sleep(0.1)
                progress_group.create_task(worker(i))
        progress.finish()
    
    asyncio.run(main())