
## Details

sadly files seeking inside a zip works by reading the offset bytes so it's slow
https://github.com/python/cpython/blob/main/Lib/zipfile.py#L1116

also id3v1 tags are stored in the end of a file :)
https://github.com/quodlibet/mutagen/blob/master/mutagen/id3/_id3v1.py#L34

and most of the players try to read it. So just adding an mp3 or flac
to a player will fetch the whole file from the archive

setting hacky_handle_mp3_id3v1 will patch reading function so it
always returns 4096 zero bytes when reading a block of 4096 bytes
(usually players read this amount looking for id3v1 (requires
investigation to find a less hacky way)) from an mp3 or flac file
inside a zip archive

## Greenback

Ensure that the current async task is able to use greenback.await_.

If the current task has called ensure_portal previously, calling it again is a no-op. Otherwise,
ensure_portal interposes a "coroutine shim" provided by greenback in between the event loop and the 
coroutine being used to run the task. For example, when running under Trio, trio.lowlevel.Task.coro 
is replaced with a wrapper around the coroutine it previously referred to. (The same thing happens 
under asyncio, but asyncio doesn't expose the coroutine field publicly, so some additional trickery 
is required in that case.)

After installation of the coroutine shim, each task step passes through greenback on its way into 
and out of your code. At some performance cost, this effectively provides a portal that allows 
later calls to greenback.await_ in the same task to access an async environment, even if the 
function that calls await_ is a synchronous function.

